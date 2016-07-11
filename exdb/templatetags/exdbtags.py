from django import template

register = template.Library()


class ExperienceNode(template.Node):
    # Template Node class for the hoop-jumping needed to get template variables.

    def __init__(self, ex, user):
        self.experience = template.Variable(ex)
        self.user = template.Variable(user)

    def render(self, context):
        ex = self.experience.resolve(context)
        user = self.user.resolve(context)
        return ex.get_url(user)


@register.tag
def experience_url(parser, token):
    try:
        ex = token.split_contents()[1]
        user = token.split_contents()[2]
    except ValueError:  # pragma: no cover
        raise template.TemplateSyntaxError(
            "%r tag requires exactly two arguments" %
            token.contents.split()[0])  # pragma: no cover
    return ExperienceNode(ex, user)
