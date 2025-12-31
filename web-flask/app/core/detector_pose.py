import cv2
import math
import numpy as np
from ultralytics import YOLO

class PoseDetector:
    def __init__(self):
        # 加载模型
        self.model = YOLO('yolov8n-pose.pt') 
        self.conf_threshold = 0.35

    def calculate_angle(self, a, b, c):
        """计算手臂弯曲角度 (肩-肘-腕)"""
        ba = np.array([a[0] - b[0], a[1] - b[1]])
        bc = np.array([c[0] - b[0], c[1] - b[1]])
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)

    def predict_data(self, frame):
        # 保持低分辨率推理，确保 CPU 不卡顿
        results = self.model(frame, verbose=False, conf=self.conf_threshold, imgsz=192)
        detections = []
        
        for result in results:
            if result.keypoints is None: continue
            
            # 获取所有关键点 [N, 17, 3] -> (x, y, conf)
            keypoints = result.keypoints.data.cpu().numpy()
            boxes = result.boxes.xyxy.cpu().numpy()
            
            for i, kps in enumerate(keypoints):
                # ====================================================
                # 1. 定义关键点
                # ====================================================
                # 面部关键点 (鼻子0, 左眼1, 右眼2)
                nose = kps[0]
                eye_l = kps[1]
                eye_r = kps[2]
                
                # 手臂关键点
                wrist_l = kps[9]   # 左腕
                elbow_l = kps[7]   # 左肘
                shoulder_l = kps[5] # 左肩
                
                wrist_r = kps[10]  # 右腕
                elbow_r = kps[8]   # 右肘
                shoulder_r = kps[6] # 右肩

                # ====================================================
                # 2. 基础数据准备
                # ====================================================
                # 获取检测框高度，用于自适应阈值 (不同距离的人阈值不同)
                box = boxes[i]
                box_h = box[3] - box[1]
                
                # 判定阈值：头部大小的大约 1.2 倍范围 (非常灵敏)
                # 0.3 * 身高 ≈ 头的大小
                face_proximity_threshold = box_h * 0.30  
                
                is_smoking = False

                # ====================================================
                # 3. 左手判定逻辑
                # ====================================================
                # 只有当手腕置信度 > 0.3 时才计算
                if wrist_l[2] > 0.3:
                    # A. 计算手腕到面部各点的距离，取最小值
                    dists = []
                    if nose[2] > 0.3:  dists.append(math.hypot(wrist_l[0]-nose[0], wrist_l[1]-nose[1]))
                    if eye_l[2] > 0.3: dists.append(math.hypot(wrist_l[0]-eye_l[0], wrist_l[1]-eye_l[1]))
                    # 如果检测不到面部，就无法判断
                    if dists:
                        min_dist_to_face = min(dists)
                        
                        # B. 计算手臂弯曲角度
                        arm_angle = 180 # 默认为直
                        if elbow_l[2] > 0.3 and shoulder_l[2] > 0.3:
                            arm_angle = self.calculate_angle(shoulder_l[:2], elbow_l[:2], wrist_l[:2])

                        # C. 综合判定: 
                        # 条件1: 手离脸很近 (距离 < 阈值)
                        # 条件2: 手臂是弯曲的 (角度 < 130度，防止直臂误判)
                        if min_dist_to_face < face_proximity_threshold and arm_angle < 130:
                            is_smoking = True

                # ====================================================
                # 4. 右手判定逻辑 (同理)
                # ====================================================
                if not is_smoking and wrist_r[2] > 0.3:
                    dists = []
                    if nose[2] > 0.3:  dists.append(math.hypot(wrist_r[0]-nose[0], wrist_r[1]-nose[1]))
                    if eye_r[2] > 0.3: dists.append(math.hypot(wrist_r[0]-eye_r[0], wrist_r[1]-eye_r[1]))
                    
                    if dists:
                        min_dist_to_face = min(dists)
                        
                        arm_angle = 180
                        if elbow_r[2] > 0.3 and shoulder_r[2] > 0.3:
                            arm_angle = self.calculate_angle(shoulder_r[:2], elbow_r[:2], wrist_r[:2])

                        if min_dist_to_face < face_proximity_threshold and arm_angle < 130:
                            is_smoking = True

                detections.append({
                    "box": [int(b) for b in box],
                    "is_smoking": is_smoking
                })
        
        return detections

    def draw_on_frame(self, frame, detections, force_alarm=False):
        annotated_frame = frame.copy()
        
        # 1. 报警边框特效
        if force_alarm:
            h, w = annotated_frame.shape[:2]
            cv2.rectangle(annotated_frame, (0, 0), (w, h), (0, 0, 255), 10)
            cv2.putText(annotated_frame, "SMOKING DETECTED", (20, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        # 2. 画人
        if detections:
            for det in detections:
                box = det["box"]
                is_red = det["is_smoking"] or force_alarm
                
                color = (0, 0, 255) if is_red else (0, 255, 0)
                # 红框粗一点，绿框细一点
                thickness = 3 if is_red else 1 
                
                cv2.rectangle(annotated_frame, (box[0], box[1]), (box[2], box[3]), color, thickness)
                
                if is_red:
                    # 在头顶显示红色标签
                    cv2.rectangle(annotated_frame, (box[0], box[1]-30), (box[0]+120, box[1]), color, -1)
                    cv2.putText(annotated_frame, "Smoking", (box[0]+5, box[1]-8), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                           
        return annotated_frame