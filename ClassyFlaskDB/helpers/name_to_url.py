import re

def underscoreify_uppercase(name):
	"""convert somethingWithUppercase into something_with_uppercase"""
	first_cap_re = re.compile('(.)([A-Z][a-z]+)')  # better to define this once
	all_cap_re = re.compile('([a-z0-9])([A-Z])')
	s1 = first_cap_re.sub(r'\1_\2', name)
	return all_cap_re.sub(r'\1_\2', s1).lower()