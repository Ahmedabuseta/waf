"""
View mixins for DRY code organization
"""
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect
from .models import Site


class SiteRequiredMixin:
    """Mixin to require a site object based on slug"""
    
    def dispatch(self, request, *args, **kwargs):
        self.site = get_object_or_404(Site, slug=kwargs.get('site_slug') or kwargs.get('slug'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site'] = self.site
        return context


class SuccessMessageMixin:
    """Mixin to add success messages"""
    success_message = None
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


class DeleteConfirmMixin:
    """Mixin for delete confirmation"""
    delete_message = "Item deleted successfully"
    redirect_url = None
    
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        messages.success(request, self.delete_message)
        return redirect(self.redirect_url or self.get_success_url())







