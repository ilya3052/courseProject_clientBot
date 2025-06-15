create table added (
   order_id             INT4                 not null,
   product_article      INT4                 not null
);

create  index added2_FK on added (
product_article
);

create  index added_FK on added (
order_id
);

create table client (
   client_id            SERIAL               not null,
   user_id              INT4                 not null,
   client_registerdate  DATE                 not null default current_date,
   client_nickname      VARCHAR(128)         not null
);

alter table client
   add constraint PK_CLIENT primary key (client_id);

create unique index client_PK on client (
client_id
);

create  index "client-user_FK" on client (
user_id
);

create table courier (
   courier_id           SERIAL               not null,
   user_id              INT4                 not null,
   courier_rating       FLOAT8               not null default 5.00
      constraint CKC_COURIER_RATING_COURIER check (courier_rating between 1.00 and 5.00),
   courier_is_busy_with_order BOOL                 not null default false
      constraint CKC_COURIER_IS_BUSY_W_COURIER check (courier_is_busy_with_order between false and true)
);

alter table courier
   add constraint PK_COURIER primary key (courier_id);

create unique index courier_PK on courier (
courier_id
);

create  index "courier-user_FK" on courier (
user_id
);

create table delivery (
   delivery_id          SERIAL               not null,
   courier_id           INT4                 not null,
   order_id             INT4                 not null,
   delivery_rating      INT4                 not null default 5
      constraint CKC_DELIVERY_RATING_DELIVERY check (delivery_rating between 1 and 5)
);

alter table delivery
   add constraint PK_DELIVERY primary key (delivery_id);
*/
create unique index delivery_PK on delivery (
delivery_id
);

create  index performs_FK on delivery (
courier_id
);

create  index included_FK on delivery (
order_id
);

create table "order" (
   order_id             SERIAL               not null,
   client_id            INT4                 not null,
   order_status         INT2                 not null default 0
      constraint CKC_ORDER_STATUS_ORDER check (order_status between 0 and 2),
   order_address        VARCHAR(255)         not null,
   order_review         TEXT                 not null
);

alter table "order"
   add constraint PK_ORDER primary key (order_id);

create unique index order_PK on "order" (
order_id
);

create  index execute_FK on "order" (
client_id
);

create table product (
   product_article      INT4                 not null,
   product_name         VARCHAR(128)         not null,
   product_category     VARCHAR(128)         not null,
   product_price        FLOAT8               not null,
   product_description  VARCHAR(512)         not null
);

alter table product
   add constraint PK_PRODUCT primary key (product_article);

create unique index product_PK on product (
product_article
);

create  index price_IDX on product (
product_price
);

create table users (
   user_id              SERIAL               not null,
   user_tgchat_id       INT4                 not null,
   user_role            VARCHAR(32)          not null,
   user_name            VARCHAR(64)          not null,
   user_surname         VARCHAR(64)          not null,
   user_patronymic      VARCHAR(64)          null,
   user_phonenumber     CHAR(11)             not null
);

alter table users
   add constraint PK_USERS primary key (user_id);

create unique index users_PK on users (
user_id
);

create  index tgchat_IDX on users (
user_tgchat_id
);

alter table added
   add constraint FK_ADDED_ADDED_ORDER foreign key (order_id)
      references "order" (order_id)
      on delete restrict on update restrict;

alter table added
   add constraint FK_ADDED_ADDED2_PRODUCT foreign key (product_article)
      references product (product_article)
      on delete restrict on update restrict;

alter table client
   add constraint FK_CLIENT_CLIENT_US_USERS foreign key (user_id)
      references users (user_id)
      on delete cascade on update restrict;

alter table courier
   add constraint FK_COURIER_COURIER_U_USERS foreign key (user_id)
      references users (user_id)
      on delete cascade on update restrict;

alter table delivery
   add constraint FK_DELIVERY_INCLUDED_ORDER foreign key (order_id)
      references "order" (order_id)
      on delete cascade on update restrict;

alter table delivery
   add constraint FK_DELIVERY_PERFORMS_COURIER foreign key (courier_id)
      references courier (courier_id)
      on delete restrict on update restrict;

alter table "order"
   add constraint FK_ORDER_EXECUTE_CLIENT foreign key (client_id)
      references client (client_id)
      on delete restrict on update restrict;