/*
 Navicat Premium Data Transfer

 Source Server         : 127.0.0.1
 Source Server Type    : MySQL
 Source Server Version : 80040
 Source Host           : localhost:3306
 Source Schema         : rent_house

 Target Server Type    : MySQL
 Target Server Version : 80040
 File Encoding         : 65001

 Date: 28/11/2025 13:53:33
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for house_appointment
-- ----------------------------
DROP TABLE IF EXISTS `house_appointment`;
CREATE TABLE `house_appointment`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `house_id` int NOT NULL,
  `appointment_date` datetime NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'pending',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for house_images
-- ----------------------------
DROP TABLE IF EXISTS `house_images`;
CREATE TABLE `house_images`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '图片记录主键ID',
  `house_id` int UNSIGNED NOT NULL COMMENT '房源ID，关联house_info表',
  `image_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '图片URL地址',
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '图片上传时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `house_id`(`house_id` ASC) USING BTREE,
  CONSTRAINT `house_images_ibfk_1` FOREIGN KEY (`house_id`) REFERENCES `house_info` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '房源图片表，存储房源相关的图片信息' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for house_info
-- ----------------------------
DROP TABLE IF EXISTS `house_info`;
CREATE TABLE `house_info`  (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `rooms` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `area` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `price` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `direction` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `rent_type` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `region` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `block` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `address` varchar(200) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `traffic` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `publish_time` int NULL DEFAULT NULL,
  `facilities` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL,
  `highlights` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL,
  `matching` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL,
  `travel` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL,
  `page_views` int NULL DEFAULT NULL,
  `landlord` varchar(30) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `phone_num` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `house_num` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `is_available` tinyint(1) NULL DEFAULT 1,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `image_url` varchar(200) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_house_landlord`(`landlord` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 113621 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for house_recommend
-- ----------------------------
DROP TABLE IF EXISTS `house_recommend`;
CREATE TABLE `house_recommend`  (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int NULL DEFAULT NULL,
  `house_id` int NULL DEFAULT NULL,
  `title` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `address` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `block` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `score` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 17995 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for house_reviews
-- ----------------------------
DROP TABLE IF EXISTS `house_reviews`;
CREATE TABLE `house_reviews`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '评价记录主键ID',
  `house_id` int UNSIGNED NOT NULL COMMENT '房源ID，关联house_info表',
  `user_id` int UNSIGNED NOT NULL COMMENT '用户ID，关联user_info表',
  `rating` int NOT NULL COMMENT '评分：1-5分，1分最低，5分最高',
  `comment` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '评价内容',
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评价创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `house_id`(`house_id` ASC) USING BTREE,
  INDEX `user_id`(`user_id` ASC) USING BTREE,
  CONSTRAINT `house_reviews_ibfk_1` FOREIGN KEY (`house_id`) REFERENCES `house_info` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `house_reviews_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user_info` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '房源评价表，记录用户对房源的评分和评论' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_behaviors
-- ----------------------------
DROP TABLE IF EXISTS `user_behaviors`;
CREATE TABLE `user_behaviors`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '行为记录主键ID',
  `user_id` int UNSIGNED NULL DEFAULT NULL COMMENT '用户ID，关联user_info表',
  `behavior_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '行为类型：view-浏览、collect-收藏、share-分享、search-搜索等',
  `target_id` int NULL DEFAULT NULL COMMENT '目标对象ID，如房源ID、评论ID等',
  `target_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '目标对象类型：house-房源、review-评论、user-用户等',
  `extra_data` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '额外数据，JSON格式存储扩展信息',
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户IP地址',
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '用户浏览器代理信息',
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '行为发生时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `user_id`(`user_id` ASC) USING BTREE,
  CONSTRAINT `user_behaviors_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user_info` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 17 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户行为记录表，用于记录用户在平台上的各种操作行为' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_info
-- ----------------------------
DROP TABLE IF EXISTS `user_info`;
CREATE TABLE `user_info`  (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `password` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `email` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `addr` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `collect_id` varchar(250) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `seen_id` varchar(250) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  `is_admin` tinyint(1) NULL DEFAULT 0,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `is_landlord` tinyint(1) NULL DEFAULT 0,
  `avatar_url` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT 'https://gitee.com/Cililin/rent-house/raw/master/static/img/default_avatar.png',
  `reset_token_expires` datetime NULL DEFAULT NULL COMMENT '添加令牌过期时间字段',
  `reset_token` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 320 CHARACTER SET = utf8mb3 COLLATE = utf8mb3_general_ci ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
