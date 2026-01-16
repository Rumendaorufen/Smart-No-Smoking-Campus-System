#web-flask\app\core\detector.py
import os
import torch
from ultralytics import YOLO
import threading

# ==========================================
# 全局单例控制
# ==========================================
_DETECTOR_INSTANCE = None
_DETECTOR_LOCK = threading.Lock()

def get_detector():
    """获取全局唯一的检测器实例 (单例模式)"""
    global _DETECTOR_INSTANCE
    with _DETECTOR_LOCK:
        if _DETECTOR_INSTANCE is None:
            _DETECTOR_INSTANCE = SmokingDetector()
    return _DETECTOR_INSTANCE

class SmokingDetector:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # === 1. 配置计算设备 ===
        # 显存紧张时，自动判断
        if torch.cuda.is_available():
            self.device = 0
            gpu_name = torch.cuda.get_device_name(0)
            print(f"🚀 【GPU模式】 AI引擎已启动: {gpu_name}")
        else:
            self.device = 'cpu'
            print("⚠️ 【CPU模式】 未检测到GPU，推理速度可能较慢")

        # === 2. 加载烟头模型 (Cigarette) ===
        smoke_model_path = os.path.join(current_dir, 'best.pt')
        if not os.path.exists(smoke_model_path):
            print(f"❌ 警告：找不到烟头模型 {smoke_model_path}，将跳过烟头检测")
            self.model_smoke = None
        else:
            # 加载自定义训练的烟头模型
            self.model_smoke = YOLO(smoke_model_path)

        # === 3. 加载人员检测模型 (Person) ===
        # ⚡️ 优化：3060 Laptop 跑多路，建议用 s 或 m。
        # 如果还要跑 3路以上，建议用 yolov8n.pt
        person_model_name = 'yolov8s.pt' 
        print(f"🚀 加载人员检测模型: {person_model_name}")
        self.model_person = YOLO(person_model_name)

        # === 4. 关键参数调优 ===
        # ⬇️ 分辨率降回 640 (原 1280 太卡了，导致超时重启)
        self.inference_size = 640 
        
        # ⬇️ 降低置信度，解决"近距离/半身"识别不到的问题
        self.person_conf = 0.35  
        self.smoke_conf = 0.40   

    def detect(self, frame):
        detections = []
        
        # ==========================
        # 🕵️‍♂️ 任务一：找人 (Person Tracking)
        # ==========================
        if self.model_person:
            # persist=True: 开启追踪记忆，解决闪烁
            # conf=0.35: 让半身照也能被识别
            # imgsz=640: 性能提升 4 倍
            results_p = self.model_person.track(
                frame, 
                persist=True, 
                classes=[0], # 0 = person
                conf=self.person_conf, 
                iou=0.5, 
                imgsz=self.inference_size, 
                verbose=False,
                device=self.device
            )
            
            raw_person_detections = []
            self._parse_results(results_p, raw_person_detections, "person")
            
            # 过滤"套娃"框 (例如把头误检为另一个人)
            filtered_persons = self._filter_contained_boxes(raw_person_detections)
            detections.extend(filtered_persons)

        # ==========================
        # 🚬 任务二：找烟 (Smoke Tracking)
        # ==========================
        if self.model_smoke:
            results_s = self.model_smoke.track(
                frame, 
                persist=True, 
                conf=self.smoke_conf, 
                imgsz=self.inference_size, 
                verbose=False,
                device=self.device
            )
            self._parse_results(results_s, detections, "cigarette")
            
        return detections

    def _filter_contained_boxes(self, detections):
        """
        [算法优化] 俄罗斯套娃去重：
        解决大脸特写时，YOLO同时框出"整个人"和"人脸/上半身"造成两个框重叠闪烁的问题。
        """
        if not detections: return []
        if len(detections) < 2: return detections
            
        # 按面积从大到小排序
        sorted_dets = sorted(detections, key=lambda d: (d['box'][2]-d['box'][0]) * (d['box'][3]-d['box'][1]), reverse=True)
        keep = []
        
        for i, small_det in enumerate(sorted_dets):
            is_contained = False
            s_box = small_det['box']
            s_area = (s_box[2] - s_box[0]) * (s_box[3] - s_box[1])
            if s_area <= 0: continue

            # 和已保留的大框比对
            for big_det in keep:
                b_box = big_det['box']
                
                # 计算交集
                inter_x1 = max(s_box[0], b_box[0])
                inter_y1 = max(s_box[1], b_box[1])
                inter_x2 = min(s_box[2], b_box[2])
                inter_y2 = min(s_box[3], b_box[3])
                
                if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    
                    # 💡 判定标准：
                    # 如果小框 80% 以上面积都在大框里，且大框是小框的 1.2 倍以上，
                    # 认为小框是冗余的（比如是同一个人的局部），丢弃小框。
                    overlap_ratio = inter_area / s_area
                    if overlap_ratio > 0.80:
                        is_contained = True
                        break 
            
            if not is_contained:
                keep.append(small_det)
                
        return keep

    def _parse_results(self, results, detections_list, label_name):
        """通用解析函数"""
        if results and len(results) > 0:
            result = results[0]
            if result.boxes and result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                track_ids = result.boxes.id.int().cpu().tolist()
                confs = result.boxes.conf.cpu().numpy()
                
                for box, track_id, conf in zip(boxes, track_ids, confs):
                    detections_list.append({
                        "id": track_id, # 追踪 ID
                        "box": [int(b) for b in box],
                        "conf": float(conf),
                        "label": label_name 
                    })