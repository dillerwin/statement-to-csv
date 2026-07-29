import sys, csv, re
from pypdf import PdfReader
import datetime as dt

# takes up to 2 arguments, the path to the pdf and a path to the csv write location

if len(sys.argv) == 1:
	sys.exit("You must include the path to the pdf")


def parse_statement():

	pdf_path = sys.argv[1]
	csv_name = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace(".pdf", ".csv")

	print(f"Translating statement at {pdf_path} into {csv_name}")

	pdf = PdfReader(pdf_path)
	pages = len(pdf.pages)
	debit_entries = []
	credit_enties = []
	starting_balance = float(0)
	ending_balance = float(0)

	for i in range(pages):
		page = pdf.pages[i]
		text = page.extract_text()
		lines = text.split("\n")
		starting_activity = False
		ending_activity = True
		full_entry = ""
		post_date = None

		for line in lines:
			# indicate the beginning of the relevant portion of the bank statement
			if "account activity" in line.lower():
				starting_activity = True
				continue
				# end account activity check

			# if not in the relevant portion of the document, keep moving
			if not starting_activity:
				continue

			# capture account starting balance
			# starting_activity if statement above prevents capturing this section more than once
			if "beginning balance" in line.lower():
				dollar_idx = line.find("$")
                # replace removes commas from larger amounts
				starting_balance += float(line[dollar_idx+1:].replace(",", ""))
				continue
				# end beginning balance

			description = ""
			debit = None
			credit = None
			charge_amount = 0
			balance = 0
			trans_type = None

			# if this is the first entry in this line, collect the date
			if full_entry == "":
				date_str = line[:10]
				date_format = "%m/%d/%Y"

				try:
					post_date = dt.datetime.strptime(date_str, date_format).strftime("%m/%d/%Y")
				except ValueError:
					# if collecting the date results in an error, the line doesn't begin with a date and is part of the previous entry
					continue

			# collect the final balance
			if "ending balance" in line.lower():
				if ending_activity:
					ending_activity = False
					# regex finds the last number in the line, then uses the $ and that number to collect the actual dollar amount
					match = re.match('.+([0-9])[^0-9]*$',line).group(1)
                    # replace removes commas from larger amounts7
					eb = float(line[line.find("$")+1:line.rfind(match)+1].replace(",", ""))
					ending_balance += eb
				continue

			# append the current line to the full entry
			full_entry += line
			# separate the date we've already collected
			split_entry = full_entry[10:].split("$")
			# collect the description of the transaction
			description = split_entry[0].strip()

			# if the entry list has fewer than 3 items, it isn't complete
			if len(split_entry) < 3:
				continue

			# if the line incldudes "account summary" or "internet transfer", it shouldn't be included. "account summary" isn't a transaction and "internet transfer" are internal transfers from one account to another
			if  "account summary" in description.lower() or "internet transfer" in description.lower():
				# full entry is reset since this line won't be captured
				full_entry = ""
				continue

			# if an entry isn't a withdrawal, list is as a credit transaction. Similarly, "rejected" indicates a balance restoration from a returned payment, which also credits to the account
			if "withdrawal" not in description.lower() or "rejected" in description.lower():
				credit = split_entry[1].replace("-", "").strip()
				trans_type = "credit"
			else:
				# otherwise list the transaction as a debit
				debit = split_entry[1].replace("-", "").strip()
				trans_type = "debit"

			# Collect the running balance
			balance = split_entry[2]

			# Remove these phrases from the descriptions, as they are effectively just visual clutter
			description = description.replace("Point Of Sale Withdrawal", "").replace("External Withdrawal", "").replace("External Deposit", "").strip()

			# create dictionary for the transaction
			entry_dict = {"Post Date": post_date, "Description": description, "Debit": debit, "Credit": credit, "Balance": balance}

			# append new dictionary to correct list
			if trans_type == "debit":
				debit_entries.append(entry_dict)
			else:
				credit_enties.append(entry_dict)

			# reset full_entry
			full_entry = ""
			#end for in lines
		#end pages loop

	print(f"Starting Balance: {round(starting_balance, 2)}\nEnding Balance: {round(ending_balance, 2)}")

	# combine all transactions together
	data = debit_entries + credit_enties

	# write transactions to a csv file
	with open(csv_name, mode="w") as csv_file:
		field_names = ["Post Date", "Description", "Debit", "Credit", "Balance"]
		writer = csv.DictWriter(csv_file, fieldnames=field_names)
		writer.writeheader()

		for datum in data:
			writer.writerow(datum)

		print(f"CSV written to {csv_name}")


	# end parse_statement


parse_statement()
