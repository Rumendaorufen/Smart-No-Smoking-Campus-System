import cv2
import numpy as np
from ultralytics import YOLO
import os
import time

class SmokingClassifier:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, 'best.pt')
        
        # 调试目录
        self.debug_dir = os.path.join(current_dir, 'debug_evidence')
        os.makedirs(self.debug_dir, exist_ok=True)
        
        try:
            self.model = YOLO(model_path)
            print("✅ 二级分类模型加载成功！")
        except:
            self.model = None

    def preprocess(self, frame, nose, wrist):
        h_img, w_img = frame.shape[:2]
        x1 = min(int(nose[0]), int(wrist[0]))
        y1 = min(int(nose[1]), int(wrist[1]))
        x2 = max(int(nose[0]), int(wrist[0]))
        y2 = max(int(nose[1]), int(wrist[1]))
        
        padding = 60 
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w_img, x2 + padding)
        y2 = min(h_img, y2 + padding)
        
        roi = frame[y1:y2, x1:x2]
        return roi

    def classify(self, frame, nose, wrist):
        if self.model is None: return False, 0.0, None

        roi = self.preprocess(frame, nose, wrist)
        if roi.size == 0: return False, 0.0, None

        try:
            results = self.model(roi, verbose=False)
            probs = results[0].probs
            class_id = int(probs.top1)
            conf = float(probs.top1conf)
            class_name = results[0].names[class_id]

            is_smoking = False
            
            # 必须严格等于 smoking
            if class_name == 'smoking' or class_name == 'smokers':
                # 置信度门槛 0.85
                if conf > 0.85:
                    is_smoking = True
                    
                    # 保存截图用于调试，如果还有误报，这些图就是训练素材
                    timestamp = int(time.time() * 1000)
                    save_path = os.path.join(self.debug_dir, f"alarm_{timestamp}_{conf:.2f}.jpg")
                    cv2.imwrite(save_path, roi)

            return is_smoking, conf, roi

        except Exception as e:
            return False, 0.0, None