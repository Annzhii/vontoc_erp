import frappe
import math
from frappe.utils import flt, cint
from frappe.locale import get_date_format, get_first_day_of_the_week, get_number_format, get_time_format

def money_in_words(
	number: str | float | int,
	main_currency: str | None = None,
	fraction_currency: str | None = None,
):
	from frappe.utils import get_defaults

	_ = frappe._

	try:
		# note: `flt` returns 0 for invalid input and we don't want that
		number = float(number)
	except ValueError:
		return ""

	number = flt(number)
	if number < 0:
		return ""

	d = get_defaults()
	if not main_currency:
		main_currency = d.get("currency", "INR")

	if not fraction_currency:
		fraction_currency = frappe.db.get_value("Currency", main_currency, "fraction", cache=True)

	number_format = get_number_format()

	fraction_units = frappe.db.get_value("Currency", main_currency, "fraction_units", cache=True)
	if fraction_units:
		fraction_length = math.ceil(math.log10(fraction_units))
	elif not fraction_units or not fraction_currency:
		fraction_units = fraction_length = 0

	n = f"%.{fraction_length}f" % number

	numbers = n.split(".")
	main, fraction = numbers if len(numbers) > 1 else [n, "00"]

	if len(fraction) < fraction_length:
		zeros = "0" * (fraction_length - len(fraction))
		fraction += zeros

	in_million = True
	if number_format.string == "#,##,###.##":
		in_million = False
	def fraction_in_words() -> str:
		return in_words(float(f"0.{fraction}") * fraction_units, in_million, main_currency).title()

	# 0.00
	if main == "0" and fraction in ["0", "00", "000"]:
		out = _(main_currency, context="Currency") + " " + _("Zero")
	elif main_currency == "CNY":
		out = _(main_currency, context="Currency") + " " + in_words_cny(n).title()
		return _("{0}", context="Money in words").format(out)
	elif main == "0":
		out = f"{fraction_in_words()} {fraction_currency}"
	else:
		out = _(main_currency, context="Currency") + " " + in_words(main, in_million, main_currency).title()
		if cint(fraction):
			out = out + " " + _("and") + " " + fraction_in_words() + " " + fraction_currency

	return _("{0} only.", context="Money in words").format(out)

def in_words_cny(n):
    import cn2an
    ret = cn2an.an2cn(str(n), mode='rmb')
    return ret.replace("-", " ")

def in_words(integer: int, in_million=True) -> str:
	"""Return string in words for the given integer."""
	from num2words import num2words

	locale = "en_IN" if not in_million else frappe.local.lang
	integer = int(integer)
	try:
		ret = num2words(integer, lang=locale)
	except NotImplementedError:
		ret = num2words(integer, lang="en")
	except OverflowError:
		ret = num2words(integer, lang="en")
	return ret.replace("-", " ")