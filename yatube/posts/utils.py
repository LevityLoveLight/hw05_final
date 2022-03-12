from django.core.paginator import Paginator


from yatube import settings


def posts_per_page(request, post_list):
    paginator = Paginator(post_list, settings.POSTS_0N_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj