import os
import torch
from ultralytics import YOLO

class SmokingDetector:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # === 1. 加载烟头模型 (你的训练成果) ===
        smoke_model_path = os.path.join(current_dir, 'best.pt')
        if not os.path.exists(smoke_model_path):
            print(f"❌ 警告：找不到烟头模型 {smoke_model_path}")
            self.model_smoke = None
        else:
            self.model_smoke = YOLO(smoke_model_path)

        # === 2. 加载官方通用模型 (用来找人) ===
        # yolov8n.pt 会自动下载，专门用来找 Person (类别ID=0)
        print("🚀 加载人员检测模型: yolov8n.pt")
        self.model_person = YOLO('yolov8n.pt') 

        # === 3. 配置设备 ===
        if torch.cuda.is_available():
            self.device = 0
            print(f"🚀 【GPU模式】 双模型已启用: {torch.cuda.get_device_name(0)}")
        else:
            self.device = 'cpu'

        self.conf_threshold = 0.25

    def detect(self, frame):
        detections = []
        
        # ==========================
        # 🕵️‍♂️ 任务一：找人 (使用官方模型)
        # ==========================
        if self.model_person:
            # classes=[0] 表示只检测 "Person" 这一类，忽略汽车、狗等
            results_p = self.model_person.track(
                frame, 
                persist=True, 
                classes=[0], 
                conf=0.5, # 人很大，置信度设高点减少误报
                verbose=False,
                device=self.device
            )
            self._parse_results(results_p, detections, "person")

        # ==========================
        # 🚬 任务二：找烟 (使用你的模型)
        # ==========================
        if self.model_smoke:
            results_s = self.model_smoke.track(
                frame, 
                persist=True, 
                conf=self.conf_threshold, 
                verbose=False,
                device=self.device
            )
            self._parse_results(results_s, detections, "cigarette")
            
        return detections

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
                        "label": label_name # 标记是人还是烟
                    })