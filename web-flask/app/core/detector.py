import os
import torch
import numpy as np
from ultralytics import YOLO
import threading

# 全局单例
_DETECTOR_INSTANCE = None
_DETECTOR_LOCK = threading.Lock()

def get_detector():
    global _DETECTOR_INSTANCE
    with _DETECTOR_LOCK:
        if _DETECTOR_INSTANCE is None:
            _DETECTOR_INSTANCE = SmokingDetector()
    return _DETECTOR_INSTANCE

class SmokingDetector:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.use_half = False # 是否开启半精度

        if torch.cuda.is_available():
            self.device = 0
            # 💡 核心优化 1：开启 FP16 半精度
            # RTX 30 系列对 FP16 支持极好，速度翻倍且精度几乎不降
            self.use_half = True 
            print(f"🚀 【GPU模式】 AI引擎已启动 (FP16加速): {torch.cuda.get_device_name(0)}")
        else:
            self.device = 'cpu'

        # === 1. 烟头模型 ===
        smoke_model_path = os.path.join(current_dir, 'best.pt')
        if os.path.exists(smoke_model_path):
            self.model_smoke = YOLO(smoke_model_path)
        else:
            self.model_smoke = None

        # === 2. 人员模型 ===
        self.model_person = YOLO('yolov8s.pt') 

        # === 3. 关键参数调优 ===
        self.person_imgsz = 640  
        self.person_conf = 0.30
        
        # 烟头检测参数
        self.smoke_imgsz = 640   
        self.smoke_conf = 0.6

        self.max_persons_per_frame = 5 
        
        # 裁剪参数
        self.crop_top_ratio = 0.6 
        self.crop_side_padding = 0.3 

        # ⚡️ 优化 2：减少记忆寿命
        # 从 5 改为 3。减少"拖泥带水"，让框跟手跟得更紧
        # 3帧约等于 100ms，足够消除闪烁，又不会产生明显拖影
        self.grace_frames = 3  
        self.smoke_memory = {} 

    def detect(self, frame):
        detections = []
        if not self.model_person: return []

        h_img, w_img = frame.shape[:2]

        # ==========================
        # 1. 全局找人 (FP16)
        # ==========================
        results_p = self.model_person.track(
            frame, 
            persist=True, 
            classes=[0], 
            conf=self.person_conf, 
            iou=0.5, 
            imgsz=self.person_imgsz, 
            verbose=False,
            device=self.device,
            half=self.use_half,
            tracker="bytetrack.yaml"  # 👈 显式指定使用 ByteTrack，比默认的 BoT-SORT 更稳
        )
        
        current_frame_pids = set()
        target_persons = []
        
        if results_p and len(results_p) > 0 and results_p[0].boxes:
            res = results_p[0]
            boxes = res.boxes.xyxy.cpu().numpy()
            track_ids = res.boxes.id.int().cpu().tolist() if res.boxes.id is not None else [-1]*len(boxes)
            confs = res.boxes.conf.cpu().numpy()
            
            for box, tid, conf in zip(boxes, track_ids, confs):
                if tid == -1: continue
                current_frame_pids.add(tid)
                x1, y1, x2, y2 = map(int, box)
                
                p_data = {
                    "id": tid,
                    "box": [x1, y1, x2, y2],
                    "conf": float(conf),
                    "label": "person",
                    "area": (x2-x1)*(y2-y1)
                }
                target_persons.append(p_data)
                detections.append(p_data)

        # 清理记忆
        expired_pids = [pid for pid in self.smoke_memory if pid not in current_frame_pids]
        for pid in expired_pids:
            del self.smoke_memory[pid]

        # ==========================
        # 2. Batch ROI 找烟 (FP16)
        # ==========================
        if self.model_smoke and len(target_persons) > 0:
            target_persons.sort(key=lambda x: x['area'], reverse=True)
            active_persons = target_persons[:self.max_persons_per_frame]

            batch_rois = []
            batch_meta = [] 

            for p in active_persons:
                px1, py1, px2, py2 = p['box']
                pw, ph = px2 - px1, py2 - py1
                
                pad_w = int(pw * self.crop_side_padding)
                crop_x1 = max(0, px1 - pad_w)
                crop_x2 = min(w_img, px2 + pad_w)
                crop_y1 = max(0, py1 - int(ph * 0.1)) 
                crop_y2 = min(h_img, py1 + int(ph * self.crop_top_ratio))

                if crop_x2 <= crop_x1 or crop_y2 <= crop_y1: continue

                roi = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                batch_rois.append(roi)
                batch_meta.append({
                    'offset': (crop_x1, crop_y1),
                    'pid': p['id'],
                    'p_origin': (px1, py1)
                })

            if len(batch_rois) > 0:
                # 🚀 Batch 推理 + FP16
                results_batch = self.model_smoke.predict(
                    batch_rois,
                    conf=self.smoke_conf,
                    imgsz=self.smoke_imgsz,
                    verbose=False,
                    device=self.device,
                    half=self.use_half, # 👈 开启半精度
                    classes=[0] 
                )

                for i, res in enumerate(results_batch):
                    meta = batch_meta[i]
                    pid = meta['pid']
                    px1, py1 = meta['p_origin']
                    found_smoke_real = False 

                    if res.boxes:
                        best_box = max(res.boxes, key=lambda x: x.conf[0])
                        sx1, sy1, sx2, sy2 = best_box.xyxy[0].cpu().numpy()
                        s_conf = float(best_box.conf[0])
                        
                        ox, oy = meta['offset']
                        gx1, gy1 = int(sx1 + ox), int(sy1 + oy)
                        gx2, gy2 = int(sx2 + ox), int(sy2 + oy)

                        # 记录相对坐标
                        rel_x = gx1 - px1
                        rel_y = gy1 - py1
                        rel_w = gx2 - gx1
                        rel_h = gy2 - gy1

                        # 刷新记忆
                        self.smoke_memory[pid] = {
                            'rel_box': [rel_x, rel_y, rel_w, rel_h],
                            'life': self.grace_frames, 
                            'conf': s_conf
                        }
                        
                        detections.append({
                            "id": pid, 
                            "box": [gx1, gy1, gx2, gy2],
                            "conf": s_conf,
                            "label": "cigarette",
                            "is_roi": True
                        })
                        found_smoke_real = True

                    # 防闪烁逻辑 (惯性追踪)
                    if not found_smoke_real and pid in self.smoke_memory:
                        mem = self.smoke_memory[pid]
                        if mem['life'] > 0:
                            mem['life'] -= 1
                            
                            # 重建坐标
                            rx, ry, rw, rh = mem['rel_box']
                            pred_x1 = px1 + rx
                            pred_y1 = py1 + ry
                            pred_x2 = pred_x1 + rw
                            pred_y2 = pred_y1 + rh
                            
                            detections.append({
                                "id": pid,
                                "box": [pred_x1, pred_y1, pred_x2, pred_y2],
                                "conf": mem['conf'],
                                "label": "cigarette",
                                "is_roi": True,
                                "is_prediction": True
                            })

        return detections

    def _filter_contained_boxes(self, detections):
        return detections