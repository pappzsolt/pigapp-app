ALTER TABLE pigapp_app_invoice DISABLE TRIGGER ALL;

INSERT INTO pigapp_app_invoice (invoice_name,invoice_note,create_invoice_date,enable_invoice,user_id,amount) VALUES
	 ('0201-en5ue0-511','0201-en5ue0-511','2020-08-26 15:18:26.572',0,1,0),
	 ('erste','erste','2021-02-11 15:39:35.182',1,1,892000),
	 ('raiffeisen','raiffeisen','2024-04-20 15:18:26.572',1,1,0);

ALTER TABLE pigapp_app_invoice ENABLE TRIGGER ALL;
COMMIT;