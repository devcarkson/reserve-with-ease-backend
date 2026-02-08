from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, EmailVerification, PasswordReset, Wishlist


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'status', 'owner_type', 'email_verified', 'created_at')
    list_filter = ('role', 'status', 'owner_type', 'email_verified', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Permissions', {'fields': ('role', 'status', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Owner Info', {'fields': ('owner_type',), 'classes': ('collapse',)}),
        ('Profile', {'fields': ('profile_picture', 'email_verified'), 'classes': ('collapse',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'role', 'status'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'country', 'preferred_language', 'currency_preference')
    list_filter = ('country', 'preferred_language', 'currency_preference')
    search_fields = ('user__username', 'user__email', 'city', 'country')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('User Info', {'fields': ('user',)}),
        ('Personal Details', {'fields': ('bio', 'date_of_birth', 'nationality')}),
        ('Contact Info', {'fields': ('address', 'city', 'country', 'postal_code')}),
        ('Preferences', {'fields': ('preferred_language', 'currency_preference', 'notification_preferences')}),
    )


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('token', 'created_at')
    
    actions = ['mark_as_used', 'delete_unused']
    
    def mark_as_used(self, request, queryset):
        queryset.update(is_used=True)
        self.message_user(request, f'{queryset.count()} email verification(s) marked as used.')
    mark_as_used.short_description = 'Mark selected as used'
    
    def delete_unused(self, request, queryset):
        deleted_count = queryset.filter(is_used=False).delete()[0]
        self.message_user(request, f'{deleted_count} unused email verification(s) deleted.')
    delete_unused.short_description = 'Delete unused verifications'


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('token', 'created_at')
    
    actions = ['mark_as_used', 'delete_unused']
    
    def mark_as_used(self, request, queryset):
        queryset.update(is_used=True)
        self.message_user(request, f'{queryset.count()} password reset(s) marked as used.')
    mark_as_used.short_description = 'Mark selected as used'
    
    def delete_unused(self, request, queryset):
        deleted_count = queryset.filter(is_used=False).delete()[0]
        self.message_user(request, f'{deleted_count} unused password reset(s) deleted.')
    delete_unused.short_description = 'Delete unused resets'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'property_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)
