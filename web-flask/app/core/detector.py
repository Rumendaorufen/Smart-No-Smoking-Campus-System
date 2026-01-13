import os
import torch
from ultralytics import YOLO

class SmokingDetector:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # === 1. 加载烟头模型 ===
        smoke_model_path = os.path.join(current_dir, 'best.pt')
        if not os.path.exists(smoke_model_path):
            print(f"❌ 警告：找不到烟头模型 {smoke_model_path}")
            self.model_smoke = None
        else:
            self.model_smoke = YOLO(smoke_model_path)

        # === 2. 加载人员检测模型 ===
        # 建议使用 yolov8m.pt 或 yolov8l.pt 以获得更好效果
        print("🚀 加载人员检测模型: yolov8m.pt")
        self.model_person = YOLO('yolov8m.pt') 

        # === 3. 配置设备 ===
        if torch.cuda.is_available():
            self.device = 0
            print(f"🚀 【GPU模式】 双模型已启用: {torch.cuda.get_device_name(0)}")
        else:
            self.device = 'cpu'

        # 烟头置信度阈值
        self.conf_threshold = 0.3

    def detect(self, frame):
        detections = []
        h, w = frame.shape[:2]
        inference_size = 1280 

        # ==========================
        # 🕵️‍♂️ 任务一：找人
        # ==========================
        if self.model_person:
            results_p = self.model_person.track(
                frame, 
                persist=True, 
                classes=[0], 
                conf=0.50,
                iou=0.6, 
                imgsz=inference_size, 
                verbose=False,
                device=self.device
            )
            
            # 🛑 步骤 1: 获取原始结果
            raw_person_detections = []
            self._parse_results(results_p, raw_person_detections, "person")
            
            # 🛑 步骤 2: 执行“套娃过滤”，去掉被包含的头框
            filtered_persons = self._filter_contained_boxes(raw_person_detections)
            
            # 🛑 步骤 3: 加入最终结果
            detections.extend(filtered_persons)

        # ==========================
        # 🚬 任务二：找烟
        # ==========================
        if self.model_smoke:
            results_s = self.model_smoke.track(
                frame, 
                persist=True, 
                conf=self.conf_threshold, 
                imgsz=inference_size, 
                verbose=False,
                device=self.device
            )
            self._parse_results(results_s, detections, "cigarette")
            
        return detections

    def _filter_contained_boxes(self, detections):
        """
        过滤包含框（俄罗斯套娃去重）：
        如果 Box A 完全（或大部分）在 Box B 内部，且 Box A 比 Box B 小很多，
        则认为 Box A 是误检（例如把头当成了人），将其删除。
        """
        if not detections:
            return []
            
        # 1. 按面积从大到小排序
        # box格式: [x1, y1, x2, y2]
        sorted_dets = sorted(detections, key=lambda d: (d['box'][2]-d['box'][0]) * (d['box'][3]-d['box'][1]), reverse=True)
        
        keep = []
        
        for i, small_det in enumerate(sorted_dets):
            is_contained = False
            s_box = small_det['box']
            s_area = (s_box[2] - s_box[0]) * (s_box[3] - s_box[1])
            
            # 和比它大的所有框比对 (因为已经排过序了，前面的肯定比当前的大)
            for big_det in keep:
                b_box = big_det['box']
                
                # 计算重叠部分坐标 (Intersection)
                inter_x1 = max(s_box[0], b_box[0])
                inter_y1 = max(s_box[1], b_box[1])
                inter_x2 = min(s_box[2], b_box[2])
                inter_y2 = min(s_box[3], b_box[3])
                
                if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    
                    # 💡 核心逻辑：包含率计算
                    # 如果小框有 85% 以上的面积都在大框里面
                    overlap_ratio = inter_area / s_area
                    
                    if overlap_ratio > 0.85:
                        is_contained = True
                        break # 被大框吃掉了，不用再比了
            
            if not is_contained:
                keep.append(small_det)
                
        return keep

    def _parse_results(self, results, detections_list, label_name):
        """辅助函数：解析 YOLO 结果并添加到列表"""
        if results and len(results) > 0:
            result = results[0]
            if result.boxes and result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                track_ids = result.boxes.id.int().cpu().tolist()
                confs = result.boxes.conf.cpu().numpy()
                
                for box, track_id, conf in zip(boxes, track_ids, confs):
                    detections_list.append({
                        "id": track_id,
                        "box": [int(b) for b in box],
                        "conf": float(conf),
                        "label": label_name 
                    })