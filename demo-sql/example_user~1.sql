insert into customers VALUES(123, 'MARY', 'USA');
insert into customers VALUES(456, 'JOHN', 'UK');
insert into customers VALUES(999, 'PETER', 'DE');
insert into customers VALUES(124, 'MARTY', 'USA');
insert into customers VALUES(457, 'JOE', 'UK');
insert into customers VALUES(1000, 'KLAUS', 'DE');

select * from customers;

insert INTO orders VALUES(4001, 123, SYSDATE);
insert INTO orders VALUES(4002, 456, SYSDATE);
insert INTO orders VALUES(4003, 999, SYSDATE);
insert INTO orders VALUES(4004, 456, SYSDATE);
insert INTO orders VALUES(4005, 456, SYSDATE);

SELECT
    *
FROM orders;

Insert into EXAMPLE_USER.PRODUCTS (STOCKNO,ITEMDESCRIPTION,PRICE) values (100,'COLLAR',39);
Insert into EXAMPLE_USER.PRODUCTS (STOCKNO,ITEMDESCRIPTION,PRICE) values (101,'PISTON',49);
Insert into EXAMPLE_USER.PRODUCTS (STOCKNO,ITEMDESCRIPTION,PRICE) values (102,'BELT',29);
select * from products;

INSERT INTO LINEITEMS VALUES (123, 10, 4001, 100, 1);
INSERT INTO LINEITEMS VALUES (999, 11, 4003, 100, 1);
INSERT INTO LINEITEMS VALUES (123, 12, 4001, 100, 1);
INSERT INTO LINEITEMS VALUES (456, 13, 4004, 100, 1);
INSERT INTO LINEITEMS VALUES (999, 14, 4003, 100, 1);
INSERT INTO LINEITEMS VALUES (999, 15, 4003, 100, 1);


select * from lineitems;

commit;