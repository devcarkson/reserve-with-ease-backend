from rest_framework import generics, status, permissions, parsers, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.utils import timezone
from django.conf import settings
from django.utils.crypto import get_random_string
from .models import EmailVerification, PasswordReset, Wishlist
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    UserUpdateSerializer, PasswordChangeSerializer, PasswordResetSerializer,
    EmailVerificationSerializer, TwoFactorSetupSerializer, TwoFactorVerifySerializer,
    TwoFactorDisableSerializer, TwoFactorRegenerateBackupCodesSerializer
)

# Get User model
User = get_user_model()

# Import R2 storage
from reserve_at_ease.custom_storage import R2Storage

# Use R2 storage if enabled
if settings.USE_R2:
    r2_storage = R2Storage()
else:
    r2_storage = None

# Import DEBUG from settings for error handling
DEBUG = settings.DEBUG


class UserRegistrationView(generics.CreateAPIView):
    """Handle user registration"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def create(self, request, *args, **kwargs):
        # Validate and create user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if email already exists
        email = request.data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            return Response({
                'error': 'A user with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username already exists
        username = request.data.get('username')
        if username and User.objects.filter(username__iexact=username).exists():
            return Response({
                'error': 'A user with this username already exists'
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

        # Handle email verification or welcome based on user role and verification status
        try:
            if user.role == 'owner' and not user.email_verified:
                # Owners who haven't verified email need verification
                print(f"DEBUG: Sending verification email to {user.email} (owner)")
                token = get_random_string(32)
                EmailVerification.objects.create(user=user, token=token)
                verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}/"
                
                # Send HTML email with verification link
                try:
                    _send_verification_email(user, verification_url)
                    print(f"DEBUG: Verification email sent to {user.email}")
                except Exception as e:
                    print(f"Error sending verification email: {e}")
            else:
                # Regular users or verified owners get welcome email
                print(f"DEBUG: Sending welcome email to {user.email}")
                try:
                    _send_welcome_email(user)
                    print(f"DEBUG: Welcome email sent to {user.email}")
                except Exception as e:
                    print(f"Error sending welcome email: {e}")
        except Exception as e:
            print(f"Error in email handling: {e}")

        # Generate JWT tokens
        try:
            refresh = RefreshToken.for_user(user)
        except Exception as e:
            return Response({
                'error': 'Failed to generate authentication tokens',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Update user profile if provided
        try:
            if hasattr(user, 'profile'):
                if request.data.get('phone'):
                    user.profile.phone = request.data.get('phone')
                if request.data.get('address'):
                    user.profile.address = request.data.get('address')
                if request.data.get('city'):
                    user.profile.city = request.data.get('city')
                if request.data.get('state'):
                    user.profile.state = request.data.get('state')
                if request.data.get('country'):
                    user.profile.country = request.data.get('country')
                if request.data.get('date_of_birth'):
                    user.profile.date_of_birth = request.data.get('date_of_birth')
                if request.data.get('profile_picture'):
                    if r2_storage:
                        # Upload to R2 using the save method
                        try:
                            from django.core.files.uploadedfile import UploadedFile
                            file_obj = request.data.get('profile_picture')
                            if isinstance(file_obj, UploadedFile):
                                file_name = file_obj.name
                            else:
                                file_name = 'profile_picture'
                            saved_path = r2_storage.save(f'profiles/{user.id}/{file_name}', file_obj)
                            user.profile.profile_picture = saved_path
                        except Exception as e:
                            print(f"Error uploading profile picture to R2: {e}")
                    else:
                        user.profile.profile_picture = request.data.get('profile_picture')
                user.profile.save()
        except Exception as e:
            # Log the error but don't fail registration
            print(f"Error updating user profile: {e}")
        
        # Prepare response
        user_data = UserSerializer(user).data
        user_data.pop('password', None)  # Remove password from response
        
        return Response({
            'message': 'User registered successfully',
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """Handle user login"""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Check if user is active
        if not user.is_active:
            return Response({
                'error': 'Your account has been deactivated. Please contact support.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Prepare user data
        user_data = UserSerializer(user).data
        user_data.pop('password', None)  # Remove password from response
        
        return Response({
            'message': 'Login successful',
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Handle user profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle password update separately
        if 'password' in request.data:
            serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            update_session_auth_hash(request, instance)  # Keep user logged in
            return Response({
                'message': 'Password updated successfully'
            })
        
        # Use UserUpdateSerializer for all profile updates
        serializer = UserUpdateSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Refresh user data with updated profile
            user_data = UserSerializer(instance).data
            user_data.pop('password', None)
            return Response({
                'message': 'Profile updated successfully',
                'user': user_data
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request_view(request):
    """Handle password reset request"""
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        # Return success even if user doesn't exist (security)
        return Response({
            'message': 'Password reset email sent'
        }, status=status.HTTP_200_OK)
    
    # Create password reset token
    token = get_random_string(32)
    PasswordReset.objects.create(user=user, token=token)
    
    # Send reset email
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}/"
    try:
        _send_password_reset_email(user, reset_url)
    except Exception as e:
        print(f"Error sending password reset email: {e}")
    
    return Response({'message': 'Password reset email sent'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password_view(request, token):
    """Handle password reset confirmation"""
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
        
        # Send confirmation email
        try:
            _send_password_reset_confirmation_email(user)
        except Exception as e:
            print(f"Error sending password reset confirmation email: {e}")
        
        return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
        
    except PasswordReset.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def verify_email_view(request, token):
    """Verify user email"""
    try:
        email_verification = EmailVerification.objects.get(token=token, is_used=False)
        from django.utils import timezone
        time_diff = timezone.now() - email_verification.created_at
        if time_diff.total_seconds() > 24 * 60 * 60:  # 24 hours in seconds
            return Response({'error': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)

        if email_verification.invitation_type == 'owner_invitation':
            # For owner invitations, return invitation details without marking as used yet
            # The user needs to complete registration first
            email_verification.is_used = True
            email_verification.save()
            
            return Response({
                'message': 'Email verified successfully',
                'invitation_type': 'owner_invitation',
                'email': email_verification.email,
                'owner_type': email_verification.owner_type if hasattr(email_verification, 'owner_type') else 'single',
                'property_id': email_verification.property_id
            }, status=status.HTTP_200_OK)
        
        # Mark email as verified for regular users
        user = email_verification.user
        user.email_verified = True
        user.is_active = True  # Activate the user
        user.save()
        
        # Mark verification token as used
        email_verification.is_used = True
        email_verification.save()
        
        return Response({
            'message': 'Email verified successfully. You can now login.'
        }, status=status.HTTP_200_OK)
        
    except EmailVerification.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def invitation_verification_view(request, token):
    """Verify invitation token for invited owners"""
    try:
        invitation = EmailVerification.objects.get(token=token, invitation_type='owner_invitation', is_used=False)
        
        # Check if token is expired (7 days for invitations)
        from django.utils import timezone
        time_diff = timezone.now() - invitation.created_at
        if time_diff.total_seconds() > 7 * 24 * 60 * 60:  # 7 days in seconds
            return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the invited email and owner type
        invited_email = invitation.email
        invitation_type = invitation.invitation_type
        owner_type = invitation.owner_type if hasattr(invitation, 'owner_type') else 'single'
        
        return Response({
            'message': 'Invitation verified successfully',
            'email': invited_email,
            'invitation_type': invitation_type,
            'owner_type': owner_type
        }, status=status.HTTP_200_OK)
        
    except EmailVerification.DoesNotExist:
        return Response({'error': 'Invalid or expired invitation'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def complete_owner_invitation_view(request, token):
    """Complete owner invitation registration"""
    try:
        invitation = EmailVerification.objects.get(token=token, invitation_type='owner_invitation', is_used=False)
        
        # Check if token is expired
        from django.utils import timezone
        time_diff = timezone.now() - invitation.created_at
        if time_diff.total_seconds() > 7 * 24 * 60 * 60:
            return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate required fields
        required_fields = ['email', 'first_name', 'last_name', 'username', 'password']
        for field in required_fields:
            if not request.data.get(field):
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify email matches invitation
        if request.data.get('email').lower() != invitation.email.lower():
            return Response({
                'error': 'Email does not match the invitation'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if email already exists
        if User.objects.filter(email__iexact=request.data.get('email')).exists():
            return Response({
                'error': 'A user with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username already exists
        if User.objects.filter(username__iexact=request.data.get('username')).exists():
            return Response({
                'error': 'A user with this username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            email=request.data.get('email'),
            username=request.data.get('username'),
            first_name=request.data.get('first_name'),
            last_name=request.data.get('last_name'),
            password=request.data.get('password'),
            role='owner',
            owner_type=invitation.owner_type if hasattr(invitation, 'owner_type') else 'single',
            is_active=True,  # Invited users are already verified
            email_verified=True
        )
        
        # Mark invitation as used
        invitation.is_used = True
        invitation.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Registration completed successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'owner_type': user.owner_type,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
        
    except EmailVerification.DoesNotExist:
        return Response({'error': 'Invalid or expired invitation'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Failed to complete registration',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_verification_email_view(request):
    """Resend verification email"""
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
        _send_verification_email(user, verification_url)
    except Exception as e:
        print(f"Error sending verification email: {e}")
    
    return Response({'message': 'Verification email sent'}, status=status.HTTP_200_OK)


# Two-Factor Authentication Views

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_2fa_secret_view(request):
    """Generate a new 2FA secret and QR code for the user"""
    user = request.user
    
    try:
        # Generate new secret
        secret = user.generate_2fa_secret()
        
        # Generate QR code
        qr_code = user.get_2fa_qr_code(secret)
        
        return Response({
            'secret': secret,
            'qr_code': qr_code,
            'message': '2FA secret generated. Please scan the QR code with Google Authenticator and verify with the code.'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        print(f"2FA secret generation error: {e}")
        traceback.print_exc()
        return Response({
            'error': f'Failed to generate 2FA secret: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def setup_2fa_view(request):
    """Enable 2FA after verifying the token"""
    serializer = TwoFactorSetupSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    result = serializer.save()
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_2fa_view(request):
    """Verify 2FA token during login or setup"""
    serializer = TwoFactorVerifySerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    result = serializer.save()
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def disable_2fa_view(request):
    """Disable 2FA with password confirmation"""
    serializer = TwoFactorDisableSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    result = serializer.save()
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def regenerate_backup_codes_view(request):
    """Regenerate 2FA backup codes"""
    serializer = TwoFactorRegenerateBackupCodesSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    result = serializer.save()
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_2fa_status_view(request):
    """Get 2FA status for the current user"""
    user = request.user
    
    backup_codes_count = 0
    if user.two_factor_backup_codes:
        backup_codes_count = len(user.two_factor_backup_codes)
    
    return Response({
        'two_factor_enabled': user.two_factor_enabled,
        'has_backup_codes': backup_codes_count > 0,
        'backup_codes_count': backup_codes_count,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_wishlist_view(request):
    """Add a property to user's wishlist"""
    try:
        property_id = request.data.get('property_id')
        if not property_id:
            return Response({
                'error': 'property_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        wishlist, created = Wishlist.objects.get_or_create(
            user=request.user,
            property_id=property_id
        )
        
        if created:
            return Response({
                'message': 'Property added to wishlist'
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'message': 'Property already in wishlist'
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_wishlist_view(request, property_id):
    """Remove a property from user's wishlist"""
    try:
        deleted_count, _ = Wishlist.objects.filter(
            user=request.user,
            property_id=property_id
        ).delete()
        
        if deleted_count > 0:
            return Response({
                'message': 'Property removed from wishlist'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Property not in wishlist'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_wishlist_view(request, property_id):
    """Check if a property is in user's wishlist"""
    try:
        is_in_wishlist = Wishlist.objects.filter(
            user=request.user,
            property_id=property_id
        ).exists()
        
        return Response({
            'is_in_wishlist': is_in_wishlist
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_wishlist_view(request):
    """Toggle a property in user's wishlist"""
    try:
        property_id = request.data.get('property_id')
        if not property_id:
            return Response({
                'error': 'property_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        existing = Wishlist.objects.filter(
            user=request.user,
            property_id=property_id
        ).first()
        
        if existing:
            # Remove from wishlist
            existing.delete()
            return Response({
                'is_in_wishlist': False,
                'message': 'Property removed from wishlist'
            }, status=status.HTTP_200_OK)
        else:
            # Add to wishlist
            Wishlist.objects.create(
                user=request.user,
                property_id=property_id
            )
            return Response({
                'is_in_wishlist': True,
                'message': 'Property added to wishlist'
            }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_wishlist_view(request):
    """Get user's wishlist"""
    try:
        wishlist = Wishlist.objects.filter(user=request.user)
        
        # Get property data using property_id
        from properties.models import Property
        wishlist_data = []
        for item in wishlist:
            try:
                # Fetch property by ID
                property_obj = Property.objects.filter(id=item.property_id, status='active').first()
                if property_obj:
                    # Get pricing info using same logic as PropertyListSerializer
                    from django.utils import timezone
                    today = timezone.now().date()
                    
                    # Calculate effective price (minimum from room categories with discounts)
                    prices = []
                    for room_category in property_obj.room_categories.all():
                        if room_category.base_price and room_category.base_price > 0:
                            effective_price = room_category.get_effective_price()
                            if effective_price and effective_price > 0:
                                prices.append(effective_price)
                    
                    # Get minimum effective price or fallback to property price
                    effective_price = min(prices) if prices else (float(property_obj.price_per_night) if property_obj.price_per_night and float(property_obj.price_per_night) > 0 else 0)
                    
                    # Get original price (minimum base price from room categories)
                    base_prices = []
                    for room_category in property_obj.room_categories.all():
                        if room_category.base_price and room_category.base_price > 0:
                            base_prices.append(float(room_category.base_price))
                    
                    original_price = min(base_prices) if base_prices else (float(property_obj.price_per_night) if property_obj.price_per_night and float(property_obj.price_per_night) > 0 else 0)
                    
                    # Check for active discounts
                    has_category_discount = property_obj.room_categories.filter(
                        has_discount=True,
                        discount_start_date__lte=today,
                        discount_end_date__gte=today
                    ).exists()
                    
                    has_availability_discount = property_obj.availability.filter(
                        has_discount=True
                    ).exists()
                    
                    has_discount = has_category_discount or has_availability_discount
                    
                    # Get highest discount percentage
                    discount_category = property_obj.room_categories.filter(
                        has_discount=True,
                        discount_start_date__lte=today,
                        discount_end_date__gte=today
                    ).order_by('-discount_percentage').first()
                    
                    discount_percentage = discount_category.discount_percentage if discount_category else 0
                    
                    property_data = {
                        'id': property_obj.id,
                        'name': property_obj.name,
                        'type': property_obj.type,
                        'description': property_obj.description,
                        'location': {
                            'address': property_obj.address,
                            'city': property_obj.city,
                            'country': property_obj.country,
                            'coordinates': {
                                'lat': property_obj.latitude,
                                'lng': property_obj.longitude
                            }
                        },
                        'price_per_night': effective_price,
                        'original_price': original_price if has_discount else None,
                        'currency': property_obj.currency,
                        'images': property_obj.images[:5] if property_obj.images else [],
                        'rating': property_obj.rating,
                        'review_count': property_obj.review_count,
                        'amenities': property_obj.amenities if property_obj.amenities else [],
                        'highlights': property_obj.highlights if property_obj.highlights else [],
                        'free_cancellation': property_obj.free_cancellation,
                        'breakfast_included': property_obj.breakfast_included,
                        'featured': property_obj.featured,
                        'owner': property_obj.owner.id,
                        'status': property_obj.status,
                        'has_discount': has_discount,
                        'discount_percentage': discount_percentage,
                        'is_discount_active': has_discount,
                        'created_at': property_obj.created_at.isoformat(),
                        'updated_at': property_obj.updated_at.isoformat(),
                    }
                    wishlist_data.append(property_data)
            except Exception as e:
                print(f"Error fetching property {item.property_id}: {e}")
                continue
        
        return Response({
            'wishlist': wishlist_data,
            'count': len(wishlist_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Additional views needed by urls.py

from rest_framework_simplejwt.tokens import AccessToken


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def token_refresh_view(request):
    """Refresh access token using refresh token"""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({
            'error': 'Refresh token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        return Response({
            'access': access_token
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Invalid refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)


# Additional endpoints needed by frontend
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Handle user logout - blacklists the refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """Change user password"""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    
    user = request.user
    old_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    new_password_confirm = request.data.get('new_password_confirm')
    
    if not old_password or not new_password:
        return Response({
            'error': 'Please provide both old and new password'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if new_password != new_password_confirm:
        return Response({
            'error': 'New passwords do not match'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not user.check_password(old_password):
        return Response({
            'error': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response({
            'error': e.messages
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()
    
    return Response({
        'message': 'Password changed successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def request_owner_invitation_view(request):
    """Request an invitation to become an owner"""
    email = request.data.get('email')
    owner_type = request.data.get('owner_type', 'single')
    property_id = request.data.get('property_id')
    
    if not email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.utils.crypto import get_random_string
        
        User = get_user_model()
        
        # Check if user already exists
        existing_user = User.objects.filter(email__iexact=email).first()
        
        if existing_user:
            # User exists - check if already an owner
            if existing_user.role == 'owner':
                return Response({
                    'message': 'You are already registered as an owner',
                    'is_owner': True
                }, status=status.HTTP_200_OK)
            
            # User exists but not an owner - check for pending invitation
            pending_invitation = EmailVerification.objects.filter(
                email__iexact=email,
                invitation_type='owner_invitation',
                is_used=False
            ).first()
            
            if pending_invitation:
                # Resend invitation
                token = pending_invitation.token
            else:
                # Create new invitation
                token = get_random_string(32)
                EmailVerification.objects.create(
                    email=email,
                    token=token,
                    invitation_type='owner_invitation',
                    owner_type=owner_type,
                    property_id=property_id
                )
        else:
            # User doesn't exist - create invitation for new user registration
            token = get_random_string(32)
            EmailVerification.objects.create(
                email=email,
                token=token,
                invitation_type='owner_invitation',
                owner_type=owner_type,
                property_id=property_id
            )
        
        # Generate invitation URL based on owner_type
        uidb64 = urlsafe_base64_encode(force_bytes(0))  # Use 0 since user might not exist yet
        if owner_type == 'single':
            invitation_url = f"{settings.FRONTEND_URL}/owner/single-verify-email?token={token}"
        else:
            invitation_url = f"{settings.FRONTEND_URL}/owner/verify-email?token={token}"
        
        if property_id:
            invitation_url += f"&property_id={property_id}"
        
        # Send invitation email (using the same wrapper function as verification emails)
        try:
            # Create a dummy user object for the email template
            class DummyUser:
                def __init__(self, email, owner_type):
                    self.email = email
                    self.first_name = ''
                    self.last_name = ''
                    self.username = email.split('@')[0]
                    self.owner_type = owner_type
                    
            dummy_user = DummyUser(email, owner_type)
            _send_verification_email(dummy_user, invitation_url)
        except Exception as email_error:
            print(f"Error sending invitation email: {email_error}")
        
        return Response({
            'message': 'Invitation sent successfully. Please check your email to complete registration.',
            'invitation_type': owner_type,
            'property_id': property_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Import email functions at the end to avoid circular imports
def _send_verification_email(user, verification_url):
    """Wrapper for sending verification email - imported from notifications.utils"""
    from notifications.utils import send_email_verification_email
    return send_email_verification_email(user, verification_url)


def _send_welcome_email(user):
    """Wrapper for sending welcome email - imported from notifications.utils"""
    from notifications.utils import send_welcome_email
    return send_welcome_email(user)


def _send_password_reset_email(user, reset_url):
    """Wrapper for sending password reset email - imported from notifications.utils"""
    from notifications.utils import send_password_reset_email
    return send_password_reset_email(user, reset_url)


def _send_password_reset_confirmation_email(user):
    """Wrapper for sending password reset confirmation email - imported from notifications.utils"""
    from notifications.utils import send_password_reset_confirmation_email
    return send_password_reset_confirmation_email(user)
