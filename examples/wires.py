import svb

svb.key = "I LOVE BANKING"


# Check out the docs on wires at
# http://docs.svbplatform.com/wire/#introduction


# Create wire
resp = svb.Wire.create(
    account_number="1234321",
    amount=10000, # integer US cents
    currency='usd',
    effective_date='2025-01-01',
    priority='high',
    receiver_account_number='987654321',
    reciever_routing_number='123456789',
)

print(resp)

# List all wires associated with your account!
resp = svb.Wire.list()

print(resp)

# Grab an individual wire for details
resp = svb.Wire.retrieve("12321")
