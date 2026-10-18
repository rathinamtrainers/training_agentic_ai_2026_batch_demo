# Broker Portal Error Codes

> Northwind Assurance · Broker Support · reference BRP-07 · reviewed 2026-07-15

## 1. How to use this list

The code shown to the broker is the code quoted here. Broker Support reads the code
back before doing anything else, because the code identifies the failing system and
saves a diagnostic call.

## 2. NW-4471 Agency not authorised for this product

The agency number is valid but does not carry the product being quoted. This is the
single most common portal error. Broker Support checks the agency's product schedule
and, where the product should be held, raises an agency amendment which takes one
working day. The broker cannot clear NW-4471 themselves.

## 3. NW-4472 Agency on stop

The agency is on credit stop under 03_agency_terms_and_credit.md clause 3. New
business is blocked; renewals and adjustments continue. Referred to credit control,
not to underwriting.

## 4. NW-2210 Vehicle not found

The registration is not in the vehicle database. The broker enters the vehicle
manually using the abbreviation code from the trade guide.

## 5. NW-3105 Referral required

The risk has hit a referral rule and cannot be bound on the portal. The submission is
routed to the underwriter automatically and the broker does not need to resend it.

## 6. NW-5000 Service unavailable

A platform fault. Broker Support raises a priority incident and posts a notice on the
portal home page. Quotes in progress are recoverable for 24 hours.
