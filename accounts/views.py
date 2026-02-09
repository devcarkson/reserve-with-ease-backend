from rest_framework import generics, status, permissions, parsers, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.utils import timezone
from .models import EmailVerification, PasswordReset, Wishlist
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    UserUpdateSerializer, PasswordChangeSerializer, PasswordResetSerializer,
    EmailVerificationSerializer, TwoFactorSetupSerializer, TwoFactorVerifySerializer,
    TwoFactorDisableSerializer, TwoFactorRegenerateBackupCodesSerializer
)

# Import R2 storage
from reserve_at_ease.custom_storage import R2Storage

# Use R2 storage if enabled
if settings.USE_R2:
    r2_storage = R2Storage()
else:
    r2_storage = None

# Import DEBUG from settings for error handling
DEBUG = settings.DEBUG

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            # Map frontend camelCase to backend snake_case
            data = request.data.copy()
            data['first_name'] = data.get('firstName', '')
            data['last_name'] = data.get('lastName', '')
            data['password_confirm'] = data.get('confirmPassword', data.get('password', ''))
            data['role'] = data.get('role', 'user')

            serializer = self.get_serializer(data=data)
            
            # Validate serializer with detailed error info
            try:
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as e:
                return Response({
                    'error': 'Validation failed',
                    'details': e.detail
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create user with detailed error handling
            try:
                user = serializer.save()
            except IntegrityError as e:
                return Response({
                    'error': 'User with this email already exists',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': 'Failed to create user',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Handle email verification or welcome based on user role
            try:
                if user.role == 'owner':
                    # Owners have already verified email via invitation, send welcome email
                    if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER and settings.EMAIL_HOST_USER != 'your-email@gmail.com':
                        try:
                            owner_type_display = "Multi-Property" if user.owner_type == 'multi' else "Single Property"
                            send_mail(
                                f'Welcome to Reserve With Ease - {owner_type_display} Owner',
                                f'Dear {user.first_name},\n\n'
                                f'Welcome to Reserve With Ease! Your {owner_type_display.lower()} owner account has been successfully created.\n\n'
                                f'You can now log in to your dashboard and start listing your properties.\n\n'
                                f'Login URL: {settings.FRONTEND_URL}/owner/login\n\n'
                                f'Best regards,\n'
                                f'The Reserve With Ease Team',
                                settings.DEFAULT_FROM_EMAIL,
                                [user.email],
                                fail_silently=False,
                            )
                        except Exception:
                            pass
                else:
                    # Regular users need email verification
                    token = get_random_string(32)
                    EmailVerification.objects.create(user=user, token=token)

                    # Send verification email
                    verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}/"

                    if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER and settings.EMAIL_HOST_USER != 'your-email@gmail.com':
                        try:
                            send_mail(
                                'Verify your email address',
                                f'Please click the following link to verify your email: {verification_url}',
                                settings.DEFAULT_FROM_EMAIL,
                                [user.email],
                                fail_silently=False,
                            )
                        except Exception:
                            pass
            except Exception:
                pass

            # Generate JWT tokens
            try:
                refresh = RefreshToken.for_user(user)
            except Exception as e:
                return Response({
                    'error': 'Failed to generate authentication tokens',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Serialize user data
            try:
                user_data = UserSerializer(user).data
            except Exception:
                user_data = {'id': user.id, 'email': user.email, 'username': user.username}

            response_data = {
                'user': user_data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': 'An unexpected error occurred during registration',
                'details': str(e) if DEBUG else 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = UserLoginSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data['user']

    # Check if 2FA is enabled
    if user.two_factor_enabled:
        response_data = {
            'user': UserSerializer(user).data,
            'message': '2FA verification required'
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # If 2FA is not enabled, generate tokens normally
    refresh = RefreshToken.for_user(user)

    response_data = {
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }
    return Response(response_data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def token_refresh_view(request):
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        access_token = str(token.access_token)
        
        return Response({
            'access': access_token
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({'error': 'Invalid refresh token'}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    # Update session to keep user logged in
    update_session_auth_hash(request, request.user)
    
    return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def request_password_reset_view(request):
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    user = User.objects.get(email=email)
    
    # Create password reset token
    token = get_random_string(32)
    PasswordReset.objects.create(user=user, token=token)
    
    # Send reset email
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}/"
    try:
        send_mail(
            'Reset your password',
            f'Please click the following link to reset your password: {reset_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except:
        pass
    
    return Response({'message': 'Password reset email sent'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password_view(request, token):
    try:
        password_reset = PasswordReset.objects.get(token=token, is_used=False)
        from django.utils import timezone
        time_diff = timezone.now() - password_reset.created_at
        if time_diff.total_seconds() > 24 * 60 * 60:  # 24 hours in seconds
            return Response({'error': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        new_password = request.data.get('new_password')
        if not new_password:
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = password_reset.user
        user.set_password(new_password)
        user.save()
        
        password_reset.is_used = True
        password_reset.save()
        
        return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
        
    except PasswordReset.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def verify_email_view(request, token):
    try:
        email_verification = EmailVerification.objects.get(token=token, is_used=False)
        from django.utils import timezone
        time_diff = timezone.now() - email_verification.created_at
        if time_diff.total_seconds() > 24 * 60 * 60:  # 24 hours in seconds
            return Response({'error': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)

        if email_verification.invitation_type == 'owner_invitation':
            # For owner invitations, just mark as used and return success
            # The frontend will handle the registration flow
            email_verification.is_used = True
            email_verification.save()
            return Response({
                'message': 'Owner invitation verified successfully',
                'invitation_type': 'owner_invitation',
                'email': email_verification.email,
                'owner_type': email_verification.owner_type,
                'property_id': email_verification.property_id
            }, status=status.HTTP_200_OK)
        else:
            # Regular email verification for existing users
            user = email_verification.user
            user.email_verified = True
            user.save()

            email_verification.is_used = True
            email_verification.save()

            return Response({'message': 'Email verified successfully'}, status=status.HTTP_200_OK)

    except EmailVerification.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def request_owner_invitation_view(request):
    email = request.data.get('email')
    owner_type = request.data.get('owner_type', 'multi')  # Default to multi-owner
    property_id = request.data.get('property_id')

    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    if owner_type not in ['single', 'multi']:
        return Response({'error': 'Invalid owner type'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if user already exists
    if User.objects.filter(email=email).exists():
        user = User.objects.get(email=email)
        if user.role == 'owner':
            return Response({'error': 'Owner account already exists with this email'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'User account already exists with this email'}, status=status.HTTP_400_BAD_REQUEST)

    # Check for existing unused invitations and update them instead of rejecting
    existing_invitation = EmailVerification.objects.filter(
        email=email,
        invitation_type='owner_invitation',
        is_used=False
    ).first()

    if existing_invitation:
        # Update existing invitation with new token and timestamp
        token = get_random_string(32)
        existing_invitation.token = token
        existing_invitation.created_at = timezone.now()  # Update timestamp
        existing_invitation.owner_type = owner_type  # Update owner type if changed
        existing_invitation.property_id = property_id  # Update property_id
        existing_invitation.save()
    else:
        # Create new invitation token
        token = get_random_string(32)
        EmailVerification.objects.create(
            email=email,
            token=token,
            invitation_type='owner_invitation',
            owner_type=owner_type,
            property_id=property_id
        )

    # Determine verification URL based on owner type
    if owner_type == 'single':
        verification_url = f"{settings.FRONTEND_URL}/owner/single-verify-email?token={token}"
    else:
        verification_url = f"{settings.FRONTEND_URL}/owner/verify-email?token={token}"

    # Send invitation email
    owner_type_display = 'Single Property' if owner_type == 'single' else 'Multi-Property'
    try:
        send_mail(
            f'{owner_type_display} Owner Registration Invitation',
            f'You have been invited to register as a {owner_type_display.lower()} property owner.\n\n'
            f'Please click the following link to verify your email and complete registration:\n\n'
            f'{verification_url}\n\n'
            f'This link will expire in 24 hours.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=True,
        )
    except Exception:
        pass

    return Response({'message': f'{owner_type_display} owner invitation sent successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_verification_email_view(request):
    user = request.user
    if user.email_verified:
        return Response({'message': 'Email already verified'}, status=status.HTTP_400_BAD_REQUEST)

    # Delete existing unused tokens
    EmailVerification.objects.filter(user=user, is_used=False).delete()

    # Create new verification token
    token = get_random_string(32)
    EmailVerification.objects.create(user=user, token=token)

    # Send verification email
    verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}/"
    try:
        send_mail(
            'Verify your email address',
            f'Please click the following link to verify your email: {verification_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except:
        pass

    return Response({'message': 'Verification email sent'}, status=status.HTTP_200_OK)


# Two-Factor Authentication Views

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_2fa_secret_view(request):
    """Generate a new 2FA secret and QR code for the user"""
    user = request.user
    
    # Generate new secret
    secret = user.generate_2fa_secret()
    
    # Generate QR code
    qr_code = user.get_2fa_qr_code(secret)
    
    return Response({
        'secret': secret,
        'qr_code': qr_code,
        'message': '2FA secret generated. Please scan the QR code with Google Authenticator and verify with the code.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def setup_2fa_view(request):
    """Enable 2FA after verifying the token"""
    serializer = TwoFactorSetupSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    result = serializer.save()
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_2fa_view(request):
    """Verify 2FA token during login"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not user.check_password(password):
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not user.two_factor_enabled:
        return Response({'error': '2FA is not enabled for this account'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = TwoFactorVerifySerializer(data=request.data, context={'user': user})
    serializer.is_valid(raise_exception=True)
    
    # Generate JWT tokens after successful 2FA verification
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        },
        'message': '2FA verification successful'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_2fa_status_view(request):
    """Get current 2FA status for the user"""
    user = request.user
    
    return Response({
        'two_factor_enabled': user.two_factor_enabled,
        'has_backup_codes': len(user.two_factor_backup_codes) > 0 if user.two_factor_backup_codes else False,
        'backup_codes_count': len(user.two_factor_backup_codes) if user.two_factor_backup_codes else 0,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def disable_2fa_view(request):
    """Disable 2FA for the user"""
    serializer = TwoFactorDisableSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    result = serializer.save()
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def regenerate_backup_codes_view(request):
    """Regenerate backup codes for 2FA"""
    serializer = TwoFactorRegenerateBackupCodesSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    result = serializer.save()
    
    return Response(result, status=status.HTTP_200_OK)


# Wishlist Views

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_wishlist_view(request):
    """Get all wishlist items for the current user"""
    from properties.serializers import PropertyListSerializer
    from properties.models import Property
    
    wishlist = Wishlist.objects.filter(user=request.user).order_by('-created_at')
    property_ids = [w.property_id for w in wishlist]
    properties = Property.objects.filter(id__in=property_ids)
    serializer = PropertyListSerializer(properties, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_wishlist_view(request):
    """Add a property to the user's wishlist"""
    property_id = request.data.get('property_id')
    if not property_id:
        return Response({'error': 'Property ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from properties.models import Property
        Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)
    
    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user,
        property_id=property_id
    )
    
    if created:
        return Response({'message': 'Property added to wishlist'}, status=status.HTTP_201_CREATED)
    else:
        return Response({'message': 'Property already in wishlist'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_wishlist_view(request, property_id):
    """Remove a property from the user's wishlist"""
    try:
        wishlist = Wishlist.objects.get(
            user=request.user,
            property_id=property_id
        )
        wishlist.delete()
        return Response({'message': 'Property removed from wishlist'}, status=status.HTTP_200_OK)
    except Wishlist.DoesNotExist:
        return Response({'error': 'Property not in wishlist'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_wishlist_view(request, property_id):
    """Check if a property is in the user's wishlist"""
    is_in_wishlist = Wishlist.objects.filter(
        user=request.user,
        property_id=property_id
    ).exists()
    
    return Response({'is_in_wishlist': is_in_wishlist}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_wishlist_view(request):
    """Toggle a property's wishlist status"""
    property_id = request.data.get('property_id')
    if not property_id:
        return Response({'error': 'Property ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    wishlist = Wishlist.objects.filter(
        user=request.user,
        property_id=property_id
    ).first()
    
    if wishlist:
        wishlist.delete()
        return Response({'is_in_wishlist': False, 'message': 'Property removed from wishlist'}, status=status.HTTP_200_OK)
    else:
        try:
            from properties.models import Property
            Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)
        
        Wishlist.objects.create(user=request.user, property_id=property_id)
        return Response({'is_in_wishlist': True, 'message': 'Property added to wishlist'}, status=status.HTTP_201_CREATED)
