-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Sep 19, 2025 at 10:50 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `monitor_test`
--

-- --------------------------------------------------------

--
-- Table structure for table `monitor_and_configs`
--

CREATE TABLE `monitor_and_configs` (
  `id` int(11) NOT NULL,
  `monitor_item_id` int(11) NOT NULL,
  `config_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `monitor_and_configs`
--

INSERT INTO `monitor_and_configs` (`id`, `monitor_item_id`, `config_id`, `created_at`, `updated_at`) VALUES
(9, 8, 6, '2025-09-19 15:44:28', NULL),
(10, 10, 7, '2025-09-19 15:49:52', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `monitor_configs`
--

CREATE TABLE `monitor_configs` (
  `id` int(11) NOT NULL,
  `name` varchar(128) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `image_list` varchar(255) DEFAULT NULL,
  `log` text DEFAULT NULL,
  `alert_type` varchar(64) DEFAULT NULL,
  `alert_config` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `monitor_configs`
--

INSERT INTO `monitor_configs` (`id`, `name`, `user_id`, `status`, `created_at`, `updated_at`, `deleted_at`, `image_list`, `log`, `alert_type`, `alert_config`) VALUES
(6, 'Test Telegram Config', 1, 1, '2025-09-19 15:44:28', NULL, NULL, NULL, NULL, 'telegram', '8040174107:AAE-XqU-XaV0Y7v30pjZgbfGzHq88LQx0HQ,-4878499254'),
(7, 'AsyncIO Test Webhook Config', 1, 1, '2025-09-19 15:49:52', NULL, NULL, NULL, NULL, 'webhook', 'http://localhost:7001/webhook');

-- --------------------------------------------------------

--
-- Table structure for table `monitor_items`
--

CREATE TABLE `monitor_items` (
  `id` int(11) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `enable` int(11) DEFAULT NULL,
  `last_check_status` int(11) DEFAULT NULL,
  `url_check` varchar(500) DEFAULT NULL,
  `type` varchar(64) DEFAULT NULL,
  `maxAlertCount` int(11) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `check_interval_seconds` int(11) DEFAULT NULL,
  `result_valid` varchar(1024) DEFAULT NULL,
  `result_error` varchar(1024) DEFAULT NULL,
  `stopTo` datetime DEFAULT NULL,
  `pingType` int(11) DEFAULT NULL,
  `log` text DEFAULT NULL,
  `last_check_time` datetime DEFAULT NULL,
  `queuedSendStr` text DEFAULT NULL,
  `forceRestart` tinyint(1) DEFAULT NULL,
  `count_online` int(11) NOT NULL,
  `count_offline` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `monitor_items`
--

INSERT INTO `monitor_items` (`id`, `name`, `enable`, `last_check_status`, `url_check`, `type`, `maxAlertCount`, `user_id`, `created_at`, `deleted_at`, `updated_at`, `check_interval_seconds`, `result_valid`, `result_error`, `stopTo`, `pingType`, `log`, `last_check_time`, `queuedSendStr`, `forceRestart`, `count_online`, `count_offline`) VALUES
(8, 'Test Telegram Monitor', 1, -1, 'http://localhost:6000', 'web_content', NULL, 1, '2025-09-19 15:44:28', NULL, '2025-09-19 15:50:23', 10, NULL, NULL, NULL, NULL, NULL, '2025-09-19 15:50:23', NULL, NULL, 7, 2),
(10, 'AsyncIO Webhook Test Monitor', 1, 1, 'http://localhost:6001', 'web_content', 5, 1, NULL, NULL, '2025-09-19 15:50:14', 10, 'AsyncIO Test Server Running', 'Connection error', NULL, NULL, NULL, '2025-09-19 15:50:14', NULL, NULL, 3, 0);

-- --------------------------------------------------------

--
-- Table structure for table `monitor_settings`
--

CREATE TABLE `monitor_settings` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `log` text DEFAULT NULL,
  `alert_time_ranges` varchar(64) DEFAULT NULL,
  `timezone` int(11) DEFAULT NULL,
  `global_stop_alert_to` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `monitor_settings`
--

INSERT INTO `monitor_settings` (`id`, `user_id`, `status`, `created_at`, `updated_at`, `deleted_at`, `log`, `alert_time_ranges`, `timezone`, `global_stop_alert_to`) VALUES
(1, 1, 1, '2025-09-19 15:38:10', NULL, NULL, NULL, '06:00-23:00', 7, NULL),
(2, 2, 1, '2025-09-19 15:38:10', NULL, NULL, NULL, '08:00-22:00', 7, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `old_id` int(11) DEFAULT NULL,
  `id__` varchar(255) DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `email` varchar(255) NOT NULL,
  `phone_number` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_admin` int(11) DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `token_user` varchar(255) DEFAULT NULL,
  `site_id` int(11) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `remember_token` varchar(100) DEFAULT NULL,
  `email_active_at` datetime DEFAULT NULL,
  `reg_str` varchar(256) DEFAULT NULL,
  `log` text DEFAULT NULL,
  `reset_pw` varchar(255) DEFAULT NULL,
  `avatar` varchar(128) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `old_id`, `id__`, `username`, `password`, `email`, `phone_number`, `created_at`, `updated_at`, `is_admin`, `deleted_at`, `token_user`, `site_id`, `name`, `remember_token`, `email_active_at`, `reg_str`, `log`, `reset_pw`, `avatar`) VALUES
(1, NULL, NULL, 'admin_user', 'hashed_password_123', 'admin@localhost.com', NULL, '2025-09-19 15:38:10', '2025-09-19 15:38:10', 1, NULL, NULL, 0, 'Administrator', NULL, NULL, NULL, NULL, NULL, NULL),
(2, NULL, NULL, 'test_user', 'hashed_password_456', 'test@localhost.com', NULL, '2025-09-19 15:38:10', '2025-09-19 15:38:10', 0, NULL, NULL, 0, 'Test User', NULL, NULL, NULL, NULL, NULL, NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `monitor_and_configs`
--
ALTER TABLE `monitor_and_configs`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `monitor_configs`
--
ALTER TABLE `monitor_configs`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `monitor_items`
--
ALTER TABLE `monitor_items`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `monitor_settings`
--
ALTER TABLE `monitor_settings`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `monitor_and_configs`
--
ALTER TABLE `monitor_and_configs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT for table `monitor_configs`
--
ALTER TABLE `monitor_configs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `monitor_items`
--
ALTER TABLE `monitor_items`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT for table `monitor_settings`
--
ALTER TABLE `monitor_settings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
