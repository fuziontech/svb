import svb

svb.key = "I LOVE BANKING"


# This is part of creating a bank account with SVB
# But is a good use case to show off mutating objects

awesome_address = svb.Address.create(
    street_line1="123 awesome ln",
    city="Jamesville",
    country="NG"
)

# Make sure we have the newest version
awesome_address.refresh()

# Oh yeah! We forgot the state
awesome_address.state = "Florida"

# Let's sync the local state with the server
awesome_address.save()

# Let's make sure server state is up to date
awesome_address.refresh()
