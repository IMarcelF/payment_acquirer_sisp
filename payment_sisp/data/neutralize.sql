-- disable sisp payment provider
UPDATE payment_provider
   SET sisp_pos_id = NULL,
       sisp_pos_aut_code = NULL,
       sisp_endpoint = NULL,
       sisp_3ds = NULL;
