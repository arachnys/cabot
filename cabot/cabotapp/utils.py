from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, Page

class Page2(Page):

    def has_next2(self):
        return self.number + 1 < self.paginator.num_pages

    def has_next3(self):
        return self.number + 2 < self.paginator.num_pages

    def has_previous2(self):
        return self.number > 2

    def has_previous3(self):
        return self.number > 3

    def next_page_number2(self):
        return self.paginator.validate_number(self.number + 2)

    def next_page_number3(self):
        return self.paginator.validate_number(self.number + 3)

    def previous_page_number2(self):
        return self.paginator.validate_number(self.number - 2)

    def previous_page_number3(self):
        return self.paginator.validate_number(self.number - 3)


class Paginator2(Paginator):
    def _get_page(self, *args, **kwargs):
        return Page2(*args, **kwargs)
