import svb

svb.api_key = "I_LOVE_BANKING"

print("Attempting to create ACH transfer")


# Refer to http://docs.svbplatform.com/ach/#create-an-ach-transfer
# for required fields
resp = svb.ACH.create(account_number='3457094867186',
                      amount=12300,
                      direction='credit',
                      receiver_account_number='3457094867185',
                      receiver_account_type='checking',
                      receiver_name="dliu",
                      receiver_routing_number='123123123',
                      sec_code='ccd')

print('Success: %r') % (resp, )
