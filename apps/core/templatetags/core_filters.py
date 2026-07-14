from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """
    Splits a string by the given separator argument.
    Usage: {{ value|split:"," }}
    """
    return value.split(arg)
