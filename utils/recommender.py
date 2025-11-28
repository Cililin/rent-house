import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from utils.database import db, HouseInfo, HouseRecommend
import numpy as np
from sqlalchemy import func


class HouseRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words=['的', '了', '在', '是', '有', '和'])
        self.scaler = StandardScaler()
        self.feature_matrix = None
        self.house_ids = []

    def prepare_features(self, houses):
        """准备房源特征"""
        features = []
        for house in houses:
            # 组合多个字段作为特征文本
            feature_parts = []
            if house.region:
                feature_parts.append(house.region)
            if house.block:
                feature_parts.append(house.block)
            if house.rent_type:
                feature_parts.append(house.rent_type)
            if house.rooms:
                feature_parts.append(house.rooms)
            if house.direction:
                feature_parts.append(house.direction)
            if house.facilities:
                feature_parts.append(house.facilities)
            if house.highlights:
                feature_parts.append(house.highlights)

            feature_str = ' '.join(feature_parts)
            features.append(feature_str)
        return features

    def train(self, houses):
        """训练推荐模型"""
        if not houses:
            self.feature_matrix = None
            self.house_ids = []
            return

        self.house_ids = [house.id for house in houses]
        features = self.prepare_features(houses)

        if features:
            # 使用TF-IDF处理文本特征
            self.feature_matrix = self.vectorizer.fit_transform(features)
        else:
            self.feature_matrix = None

    def recommend_similar_houses(self, house_id, top_n=10):
        """推荐相似房源"""
        if self.feature_matrix is None or house_id not in self.house_ids:
            return []

        try:
            house_idx = self.house_ids.index(house_id)
            similarities = cosine_similarity(
                self.feature_matrix[house_idx:house_idx + 1],
                self.feature_matrix
            ).flatten()

            # 获取最相似的前top_n+1个（包括自己）
            similar_indices = similarities.argsort()[::-1][1:top_n + 1]
            recommended_houses = []

            for idx in similar_indices:
                if idx < len(self.house_ids):
                    recommended_houses.append(self.house_ids[idx])

            return recommended_houses
        except ValueError:
            return []

    def recommend_for_user(self, user_id, user_seen_houses, top_n=10):
        """为用户推荐房源"""
        if not user_seen_houses:
            # 如果用户没有浏览历史，返回热门房源
            return self.get_popular_houses(top_n)

        # 基于用户浏览历史推荐相似房源
        all_recommendations = []
        for house_id in user_seen_houses[:5]:  # 只考虑最近5个浏览
            similar = self.recommend_similar_houses(house_id, top_n=3)
            all_recommendations.extend(similar)

        # 去重并排除已浏览的房源
        recommendations = list(set(all_recommendations) - set(user_seen_houses))

        # 如果推荐数量不足，用热门房源补充
        if len(recommendations) < top_n:
            popular = self.get_popular_houses(top_n * 2)
            # 排除已推荐和已浏览的
            popular = [p for p in popular if p not in recommendations and p not in user_seen_houses]
            recommendations.extend(popular[:top_n - len(recommendations)])

        return recommendations[:top_n]

    def get_popular_houses(self, top_n=10):
        """获取热门房源（基于浏览量）"""
        houses = HouseInfo.query.filter_by(is_available=True) \
            .order_by(HouseInfo.page_views.desc()) \
            .limit(top_n).all()
        return [house.id for house in houses]