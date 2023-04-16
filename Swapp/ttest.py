import phonenumbers
import pycountry

import pycountry
import phonenumbers

# Create a dictionary of all country codes and their names
country_codes = {}
for country in pycountry.countries:
    country_codes[country.alpha_2] = country.name

# Parse the phone number
phone_number = "+447732310142"
parsed_number = phonenumbers.parse(phone_number)
print(parsed_number)
# Get the country code
country_code = phonenumbers.region_code_for_number(parsed_number)
print(country_code)
# Look up the country name using the country code
if country_code in country_codes:
    country_name = country_codes[country_code]
else:
    country_name = "Unknown"

print(country_name)
