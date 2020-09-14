
USE manege_trace_db_reserve;

-- ----------------------------
-- Table structure for weight
-- ----------------------------
CREATE TABLE if not exists `weight` (
  `id` smallint(8) unsigned NOT NULL AUTO_INCREMENT,
  `area_q1` float(4,2) NOT NULL DEFAULT 0.00,
  `area_q2` float(4,2) NOT NULL DEFAULT 0.00,
  `area_q3` float(4,2) NOT NULL DEFAULT 0.00,
  `area_q4` float(4,2) NOT NULL DEFAULT 0.00,
  `area_inc` float(4,2) NOT NULL DEFAULT 0.00,
  `area_sto` float(4,2) NOT NULL DEFAULT 0.00,
  `product_dev_inc` float(4,2) NOT NULL DEFAULT 0.00,
  `product_soft_inc` float(4,2) NOT NULL DEFAULT 0.00,
  `product_dev_sto` float(4,2) NOT NULL DEFAULT 0.00,
  `product_soft_sto` float(4,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of weight
-- ----------------------------
REPLACE into weight (id,area_q1,area_q2,area_q3,area_q4,area_inc,area_sto,product_dev_inc, product_soft_inc,product_dev_sto,product_soft_sto)
 VALUES (1, 0.00, 0.00, 0.70, 1.00, 35.00, 20.00, 20.00, 35.00, 25.00, 10.00);

-- ----------------------------
-- product
-- ----------------------------
ALTER TABLE product
ADD `q1` float(4,2) NOT NULL DEFAULT 0.00,
ADD `q2` float(4,2) NOT NULL DEFAULT 0.00,
ADD `q3` float(4,2) NOT NULL DEFAULT 0.00,
ADD `q4` float(4,2) NOT NULL DEFAULT 0.00;

-- ----------------------------
-- Records of product
-- ----------------------------
update `product` set q1=0.0, q2=0.0, q3=0.45, q4=1.00 where product_id =1;
update `product` set q1=0.0, q2=0.0, q3=0.45, q4=0.8 where product_id =2;
update `product` set q1=0.0, q2=0.0, q3=0.16, q4=0.4 where product_id =3;
update `product` set q1=0.0, q2=0.0, q3=0.82, q4=1.00 where product_id =4;
update `product` set q1=0.0, q2=0.0, q3=0.4, q4=0.8 where product_id =5;
update `product` set q1=0.0, q2=0.0, q3=0.3, q4=0.8 where product_id =6;
update `product` set q1=0.0, q2=0.0, q3=0.5, q4=0.9 where product_id =7;
update `product` set q1=0.0, q2=0.0, q3=0.1, q4=0.4 where product_id =8;
update `product` set q1=0.0, q2=0.0, q3=0.25, q4=0.6 where product_id =9;
update `product` set q1=0.0, q2=0.0, q3=1.0, q4=1.00 where product_id =10;
