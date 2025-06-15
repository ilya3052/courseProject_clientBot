drop index "client-user_FK";

drop index client_PK;

alter table client
   drop constraint PK_CLIENT;

drop table client;

drop index "courier-user_FK";

drop index courier_PK;

alter table courier
   drop constraint PK_COURIER;

drop table courier;

drop index included_FK;

drop index performs_FK;

drop index delivery_PK;

alter table delivery
   drop constraint PK_DELIVERY;

drop table delivery;

drop index execute_FK;

drop index order_PK;

alter table "order"
   drop constraint PK_ORDER;

drop table "order";

drop index price_IDX;

drop index product_PK;

alter table product
   drop constraint PK_PRODUCT;

drop table product;

drop index tgchat_IDX;

drop index users_PK;

alter table users
   drop constraint PK_USERS;

drop table users;