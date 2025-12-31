# CNN 分类器封装
import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from typing import Dict, List, Tuple, Optional

class SmokingClassifier(nn.Module):
    """
    CNN吸烟分类器
    对姿态检测筛选出的区域进行精细分类，判断是否为吸烟行为
    """
    
    def __init__(self, num_classes: int = 2):
        """
        初始化CNN分类器
        
        Args:
            num_classes: 分类类别数 (默认2类：吸烟/非吸烟)
        """
        super(SmokingClassifier, self).__init__()
        
        # 卷积层
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        
        # 池化层
        self.pool = nn.MaxPool2d(2, 2)
        
        # 全连接层
        self.fc1 = nn.Linear(256 * 8 * 8, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, num_classes)
        
        # Dropout层
        self.dropout = nn.Dropout(0.5)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: 输入张量 (batch_size, channels, height, width)
        
        Returns:
            输出张量 (batch_size, num_classes)
        """
        # 卷积 + 池化 + 激活
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.pool(F.relu(self.conv3(x)))
        x = self.pool(F.relu(self.conv4(x)))
        
        # 展平
        x = x.view(-1, 256 * 8 * 8)
        
        # 全连接层 + Dropout
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.dropout(F.relu(self.fc2(x)))
        x = self.fc3(x)
        
        return x

class ImageClassifier:
    """
    图像分类器封装
    用于加载模型和进行预测
    """
    
    def __init__(self, model_path: str, conf_thres: float = 0.85):
        """
        初始化图像分类器
        
        Args:
            model_path: 模型文件路径
            conf_thres: 分类置信度阈值
        """
        self.model_path = model_path
        self.conf_thres = conf_thres
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            print(f"警告：CNN模型文件不存在: {model_path}")
            print("使用随机初始化模型")
            self.model = self._create_random_model()
        else:
            # 加载预训练模型
            self.model = self._load_model()
        
        # 设置为评估模式
        self.model.eval()
        
        # 定义图像变换
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def _create_random_model(self) -> SmokingClassifier:
        """
        创建随机初始化的模型
        
        Returns:
            随机初始化的分类器模型
        """
        model = SmokingClassifier()
        return model.to(self.device)
    
    def _load_model(self) -> SmokingClassifier:
        """
        加载预训练模型
        
        Returns:
            加载的分类器模型
        """
        # 加载模型
        model = SmokingClassifier()
        model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        return model.to(self.device)
    
    def classify(self, image: np.ndarray, bbox: List[int]) -> Dict:
        """
        对图像中的区域进行分类
        
        Args:
            image: 输入图像 (BGR格式)
            bbox: 目标区域边界框 [x1, y1, x2, y2]
        
        Returns:
            分类结果，包含：
            - class_id: 类别ID (0:非吸烟, 1:吸烟)
            - confidence: 置信度
            - label: 类别标签
        """
        # 截取目标区域
        x1, y1, x2, y2 = bbox
        
        # 确保坐标有效
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.shape[1], x2)
        y2 = min(image.shape[0], y2)
        
        # 计算头部扩充区域
        h = y2 - y1
        w = x2 - x1
        
        # 扩充边界框 (上下左右各扩充h/2)
        expand = int(h * 0.5)
        x1_exp = max(0, x1 - expand)
        y1_exp = max(0, y1 - expand)
        x2_exp = min(image.shape[1], x2 + expand)
        y2_exp = min(image.shape[0], y2 + expand)
        
        # 截取扩充后的区域
        roi = image[y1_exp:y2_exp, x1_exp:x2_exp]
        
        # 如果区域太小，返回默认结果
        if roi.shape[0] < 32 or roi.shape[1] < 32:
            return {
                'class_id': 0,
                'confidence': 0.0,
                'label': 'Non-Smoking'
            }
        
        # 转换为RGB格式
        roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        
        # 应用图像变换
        input_tensor = self.transform(roi_rgb).unsqueeze(0).to(self.device)
        
        # 进行预测
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = F.softmax(outputs, dim=1)
            confidence, class_id = torch.max(probabilities, 1)
            
            class_id = class_id.item()
            confidence = confidence.item()
        
        # 映射类别ID到标签
        label = 'Smoking' if class_id == 1 else 'Non-Smoking'
        
        return {
            'class_id': class_id,
            'confidence': confidence,
            'label': label
        }
    
    def classify_keypoint_region(self, image: np.ndarray, keypoints: List[List[float]]) -> Dict:
        """
        基于关键点坐标分类头部区域
        
        Args:
            image: 输入图像 (BGR格式)
            keypoints: 关键点坐标列表
        
        Returns:
            分类结果
        """
        # 提取鼻子、左右耳朵关键点
        nose = keypoints[0]
        left_ear = keypoints[3]
        right_ear = keypoints[4]
        
        # 计算头部中心点和大小
        center_x = int(nose[0])
        center_y = int(nose[1])
        
        # 计算耳朵之间的距离作为头部宽度
        ear_distance = self._calculate_distance(
            (left_ear[0], left_ear[1]),
            (right_ear[0], right_ear[1])
        )
        
        # 头部区域大小
        head_size = int(ear_distance * 1.5)
        
        # 计算头部边界框
        x1 = max(0, center_x - head_size)
        y1 = max(0, center_y - head_size)
        x2 = min(image.shape[1], center_x + head_size)
        y2 = min(image.shape[0], center_y + head_size)
        
        # 调用分类方法
        return self.classify(image, [x1, y1, x2, y2])
    
    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """
        计算两点之间的欧氏距离
        
        Args:
            point1: 第一个点 (x, y)
            point2: 第二个点 (x, y)
        
        Returns:
            两点之间的距离
        """
        return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5
    
    def draw_classification(self, image: np.ndarray, bbox: List[int], result: Dict) -> np.ndarray:
        """
        在图像上绘制分类结果
        
        Args:
            image: 输入图像
            bbox: 目标区域边界框 [x1, y1, x2, y2]
            result: 分类结果
        
        Returns:
            绘制后的图像
        """
        # 复制图像以避免修改原图
        annotated_image = image.copy()
        
        # 边界框颜色 (红色表示吸烟，绿色表示正常)
        color = (0, 0, 255) if result['class_id'] == 1 else (0, 255, 0)
        
        # 绘制边界框
        x1, y1, x2, y2 = bbox
        cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
        
        # 绘制分类结果
        text = f"{result['label']}: {result['confidence']:.2f}"
        cv2.putText(annotated_image, 
                   text, 
                   (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, 
                   color, 
                   2)
        
        return annotated_image
