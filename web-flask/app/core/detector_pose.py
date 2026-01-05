import cv2
import math
import numpy as np
from ultralytics import YOLO

class PoseDetector:
    def __init__(self):
        self.model = YOLO('yolov8n-pose.pt') 
        self.conf_threshold = 0.35

    def calculate_angle(self, a, b, c):
        ba = np.array([a[0] - b[0], a[1] - b[1]])
        bc = np.array([c[0] - b[0], c[1] - b[1]])
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)

    def predict_data(self, frame):
        # 保持 256 分辨率
        results = self.model(frame, verbose=False, conf=self.conf_threshold, imgsz=256)
        detections = []
        
        for result in results:
            if result.keypoints is None: continue
            
            keypoints = result.keypoints.data.cpu().numpy()
            boxes = result.boxes.xyxy.cpu().numpy()
            
            for i, kps in enumerate(keypoints):
                nose = kps[0]
                wrist_l, wrist_r = kps[9], kps[10]
                elbow_l, elbow_r = kps[7], kps[8]
                shoulder_l, shoulder_r = kps[5], kps[6]
                
                box = boxes[i]
                box_h = box[3] - box[1]
                
                is_suspicious = False
                suspicious_hand = None 

                # ====================================================
                # ⚖️ 参数回调：平衡模式
                # ====================================================
                # 1. 距离阈值：0.30 (允许手稍微离嘴巴有一定距离)
                face_proximity_threshold = box_h * 0.30
                
                # 2. 手腕置信度：0.60 (过滤衣领，但保留真手)
                WRIST_CONF_THRESH = 0.60
                
                # 3. 高度防线：0.20 (允许稍微低头)
                height_limit = nose[1] + (box_h * 0.20) 

                # --- 左手检测 ---
                if wrist_l[2] > WRIST_CONF_THRESH and nose[2] > 0.5:
                    if wrist_l[1] < height_limit: # 高度检查
                        dist = math.hypot(wrist_l[0]-nose[0], wrist_l[1]-nose[1])
                        if dist < face_proximity_threshold:
                            arm_angle = 180
                            if elbow_l[2] > 0.3 and shoulder_l[2] > 0.3:
                                arm_angle = self.calculate_angle(shoulder_l[:2], elbow_l[:2], wrist_l[:2])
                            
                            if arm_angle < 140: # 角度放宽到 140
                                is_suspicious = True
                                suspicious_hand = "left"

                # --- 右手检测 ---
                if not is_suspicious and wrist_r[2] > WRIST_CONF_THRESH and nose[2] > 0.5:
                    if wrist_r[1] < height_limit:
                        dist = math.hypot(wrist_r[0]-nose[0], wrist_r[1]-nose[1])
                        if dist < face_proximity_threshold:
                            arm_angle = 180
                            if elbow_r[2] > 0.3 and shoulder_r[2] > 0.3:
                                arm_angle = self.calculate_angle(shoulder_r[:2], elbow_r[:2], wrist_r[:2])
                            
                            if arm_angle < 140:
                                is_suspicious = True
                                suspicious_hand = "right"

                wrist_coord = wrist_l[:2] if suspicious_hand == "left" else wrist_r[:2]
                
                detections.append({
                    "box": [int(b) for b in box],
                    "is_suspicious": is_suspicious,
                    "nose_coord": nose[:2],
                    "wrist_coord": wrist_coord,
                    "final_smoking": False,
                    "debug_kps": {
                        "wrist_l": wrist_l, "wrist_r": wrist_r, "nose": nose, "limit": height_limit
                    }
                })
        
        return detections

    def draw_on_frame(self, frame, detections, force_alarm=False):
        annotated_frame = frame.copy()
        
        if force_alarm:
            h, w = annotated_frame.shape[:2]
            cv2.rectangle(annotated_frame, (0, 0), (w, h), (0, 0, 255), 10)
            cv2.putText(annotated_frame, "SMOKING DETECTED", (20, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        if detections:
            for det in detections:
                box = det["box"]
                
                if det["final_smoking"] or force_alarm:
                    color = (0, 0, 255) 
                    text = "Smoking"
                elif det["is_suspicious"]:
                    color = (0, 255, 255) 
                    text = "Checking..."
                else:
                    color = (0, 255, 0) 
                    text = "Normal"

                cv2.rectangle(annotated_frame, (box[0], box[1]), (box[2], box[3]), color, 2)
                cv2.putText(annotated_frame, text, (box[0], box[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # 调试辅助线 (可保留观察)
                kps = det["debug_kps"]
                limit_y = int(kps["limit"])
                cv2.line(annotated_frame, (box[0], limit_y), (box[2], limit_y), (0, 255, 255), 1)
                           
        return annotated_frame