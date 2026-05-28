CREATE TABLE `users` (
  `u_id` INT(11) NOT NULL AUTO_INCREMENT,
  `uname` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `password` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`u_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert a sample user
INSERT INTO `users` (`uname`, `email`, `password`) VALUES
('Test User', 'test@gmail.com', 'scrypt:32768:8:1$WNNVrkEMdwXXGxGF$951cdc37b1a2be9285cd85343aaaf24168a36cc619e38ef4f14ab606f73fe6b7322d1d7a3c9fe685d5b9fb898cd22f9d812be5dfecdc097b4bd3ec2dc90cb656');

CREATE TABLE posture_logs ( log_id INT AUTO_INCREMENT PRIMARY KEY, 
  user_id INT NOT NULL, 
  issue_type VARCHAR(100) NOT NULL, 
  posture_type VARCHAR(100), 
  recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  FOREIGN KEY (user_id) REFERENCES users(u_id) ON DELETE CASCADE );