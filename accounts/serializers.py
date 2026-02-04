from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile, EmailVerification


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=False, source='confirmPassword')
    firstName = serializers.CharField(write_only=True)
    lastName = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    countryCode = serializers.CharField(write_only=True, required=False, allow_blank=True)
    company = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    owner_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    property_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'firstName', 'lastName', 'password', 'password_confirm', 'phone', 'countryCode', 'company', 'address', 'owner_type', 'role', 'property_id')

    def validate(self, attrs):
        print("=== SERIALIZER VALIDATION DEBUG ===")
        print("Initial attrs:", attrs)
        
        # Handle frontend field names
        if 'firstName' in attrs:
            attrs['first_name'] = attrs.pop('firstName')
        if 'lastName' in attrs:
            attrs.pop('lastName')

        # Merge phone number and country code
        phone = attrs.get('phone', '').strip()
        country_code = attrs.get('countryCode', '').strip()
        
        print(f"Phone before merge: '{phone}'")
        print(f"Country code before merge: '{country_code}'")
        
        # Always merge phone and country code if either is provided
        if phone or country_code:
            if country_code and not country_code.startswith('+'):
                country_code = f"+{country_code}"
            if phone and not phone.startswith('+') and country_code:
                phone = f"{country_code}{phone}"
            elif country_code and not phone:
                phone = country_code
            attrs['phone'] = phone
        else:
            attrs['phone'] = ''

        print(f"Phone after merge: '{attrs['phone']}'")
        print("Final attrs:", attrs)
        print("=== END SERIALIZER VALIDATION DEBUG ===")

        # Only validate password confirmation if provided
        password_confirm = attrs.get('password_confirm')
        if password_confirm and attrs['password'] != password_confirm:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        print("=== SERIALIZER CREATE DEBUG ===")
        print("Validated data received:", validated_data)

        # Extract profile fields
        company = validated_data.pop('company', '')
        address = validated_data.pop('address', '')
        property_id = validated_data.pop('property_id', None)

        # Remove both possible field names for password confirmation
        validated_data.pop('password_confirm', None)
        validated_data.pop('confirmPassword', None)
        countryCode = validated_data.pop('countryCode', None)  # Remove country code as it's merged with phone
        print(f"Removed countryCode: {countryCode}")

        # Set default values for registration
        validated_data['username'] = validated_data['email']
        # Keep the role as provided (user or owner), default to user
        validated_data.setdefault('role', 'user')
        # Set owner_type based on provided value or role
        if validated_data.get('role') == 'owner':
            validated_data.setdefault('owner_type', 'multi')  # Default to multi for owners
            validated_data['email_verified'] = True  # Owners verify email before registration
        else:
            validated_data['owner_type'] = ''
            validated_data.setdefault('email_verified', False)

        print("Final data for user creation:", validated_data)

        # Create user with phone field explicitly handled
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone=validated_data.get('phone', ''),  # Ensure phone is passed
            role=validated_data['role'],
            owner_type=validated_data['owner_type']
        )
        print(f"User created with phone: '{user.phone}'")

        # Set email_verified if provided
        if 'email_verified' in validated_data:
            user.email_verified = validated_data['email_verified']
            user.save()
            print(f"User email_verified set to: {user.email_verified}")

        # Create user profile with additional fields
        UserProfile.objects.create(
            user=user,
            address=address,
            company=company
        )

        # Assign property if property_id is provided
        if property_id:
            try:
                from properties.models import Property
                property_obj = Property.objects.get(id=property_id)
                # Add single owner to authorized_users instead of changing ownership
                # This preserves the multi-owner's profile for the single owner
                property_obj.authorized_users.add(user)
                print(f"Property {property_id} authorized for user {user.id}")
            except Exception as e:
                print(f"Failed to authorize property {property_id} for user {user.id}: {e}")
                # Don't fail registration if property assignment fails

        print("=== END SERIALIZER CREATE DEBUG ===")
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            try:
                user = User.objects.get(email__iexact=email)
                print(f"User found: {user.email}, username: {user.username}")
            except User.DoesNotExist:
                print(f"User not found for email: {email}")
                raise serializers.ValidationError({'detail': 'No account found with this email address'})

            if not user.check_password(password):
                print(f"Password check failed for user: {user.email}")
                raise serializers.ValidationError({'detail': 'Incorrect password'})
            else:
                print(f"Password check succeeded for user: {user.email}")

            if not user.is_active:
                raise serializers.ValidationError({'detail': 'User account is disabled'})

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password')


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ('id', 'user')


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'phone',
                  'role', 'status', 'email_verified', 'profile_picture',
                  'created_at', 'updated_at', 'profile', 'owner_type',
                  'two_factor_enabled')
        read_only_fields = ('id', 'created_at', 'updated_at', 'email_verified', 'two_factor_enabled')

    def get_profile(self, obj):
        # For single owners, return the multi-owner's profile from the property
        if obj.owner_type == 'single':
            try:
                from properties.models import Property
                # Find the property where this user is an authorized user
                property_obj = Property.objects.filter(authorized_users=obj).first()
                if property_obj and property_obj.owner:
                    # Return the multi-owner's profile
                    multi_owner = property_obj.owner
                    try:
                        return UserProfileSerializer(multi_owner.profile).data
                    except:
                        return None
            except Exception as e:
                print(f"Error getting multi-owner profile for single owner {obj.id}: {e}")
        
        # Default behavior for multi owners or users without properties
        try:
            return UserProfileSerializer(obj.profile).data
        except:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Only include owner_type for users with 'owner' role
        if instance.role != 'owner':
            data.pop('owner_type', None)
        
        # Convert profile_picture to public R2 URL if R2 is enabled
        if instance.profile_picture:
            from django.conf import settings
            if settings.USE_R2:
                from properties.utils import convert_image_urls_to_public
                data['profile_picture'] = convert_image_urls_to_public([instance.profile_picture.name])[0]
            else:
                data['profile_picture'] = instance.profile_picture.url
        
        # For single owners, override user fields with multi-owner's info (except email)
        if instance.owner_type == 'single':
            try:
                from properties.models import Property
                # Find the property where this user is an authorized user
                property_obj = Property.objects.filter(authorized_users=instance).first()
                if property_obj and property_obj.owner:
                    multi_owner = property_obj.owner
                    # Override user-level fields with multi-owner's info (keep own email)
                    data['first_name'] = multi_owner.first_name
                    data['last_name'] = multi_owner.last_name
                    data['phone'] = multi_owner.phone
                    # Use URL instead of file object for profile_picture
                    if multi_owner.profile_picture:
                        from django.conf import settings
                        if settings.USE_R2:
                            from properties.utils import convert_image_urls_to_public
                            data['profile_picture'] = convert_image_urls_to_public([multi_owner.profile_picture.name])[0]
                        else:
                            data['profile_picture'] = multi_owner.profile_picture.url
                    else:
                        data['profile_picture'] = None
                    # Profile fields are already overridden in get_profile
            except Exception as e:
                print(f"Error overriding single owner fields with multi-owner info: {e}")
        
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    profile_picture = serializers.ImageField(required=False, allow_null=True, allow_empty_file=True)
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'profile_picture', 'profile')

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Handle profile_picture upload to R2
        if 'profile_picture' in validated_data:
            from django.conf import settings
            if settings.USE_R2:
                profile_picture_file = validated_data.pop('profile_picture')
                if profile_picture_file:
                    # Import R2 storage
                    from reserve_at_ease.custom_storage import R2Storage
                    
                    r2_storage = R2Storage()
                    # Save profile picture to R2
                    try:
                        profile_picture_path = r2_storage.save(f'profile_pics/{profile_picture_file.name}', profile_picture_file)
                        validated_data['profile_picture'] = profile_picture_path
                        print(f"Profile picture saved to R2: {profile_picture_path}")
                    except Exception as e:
                        print(f"Error saving to R2: {e}")
                        # Fall back to local handling if R2 fails
                        pass
        
        # For single owners, update multi-owner's info instead
        if instance.owner_type == 'single':
            try:
                from properties.models import Property
                property_obj = Property.objects.filter(authorized_users=instance).first()
                if property_obj and property_obj.owner:
                    multi_owner = property_obj.owner
                    # Update multi-owner's user fields
                    if 'first_name' in validated_data:
                        multi_owner.first_name = validated_data.pop('first_name')
                    if 'last_name' in validated_data:
                        multi_owner.last_name = validated_data.pop('last_name')
                    if 'phone' in validated_data:
                        multi_owner.phone = validated_data.pop('phone')
                    # Handle profile_picture separately if present
                    if 'profile_picture' in validated_data:
                        multi_owner.profile_picture = validated_data.pop('profile_picture')
                    multi_owner.save()
                    
                    # Update multi-owner's profile
                    if profile_data:
                        multi_profile = multi_owner.profile
                        for attr, value in profile_data.items():
                            setattr(multi_profile, attr, value)
                        multi_profile.save()
                    
                    return multi_owner
            except Exception as e:
                print(f"Error updating multi-owner profile for single owner: {e}")
        
        # Default behavior for multi owners
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile if provided
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('User with this email does not exist')
        return value


class EmailVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerification
        fields = ('token', 'created_at', 'is_used', 'email', 'invitation_type')
        read_only_fields = ('token', 'created_at', 'is_used')


class TwoFactorSetupSerializer(serializers.Serializer):
    """Serializer for setting up 2FA"""
    token = serializers.CharField(max_length=6, min_length=6, required=True)
    
    def validate_token(self, value):
        user = self.context['request'].user
        if not user.two_factor_secret:
            raise serializers.ValidationError("2FA not set up. Please generate a secret first.")
        
        if not user.verify_2fa_token(value):
            raise serializers.ValidationError("Invalid verification code")
        
        return value
    
    def save(self):
        user = self.context['request'].user
        user.two_factor_enabled = True
        user.save()
        
        # Generate backup codes after successful 2FA setup
        backup_codes = user.generate_backup_codes()
        
        return {
            'message': '2FA enabled successfully',
            'backup_codes': backup_codes
        }


class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer for verifying 2FA during login"""
    token = serializers.CharField(max_length=6, min_length=6, required=False)
    backup_code = serializers.CharField(max_length=6, min_length=6, required=False)
    
    def validate(self, attrs):
        user = self.context['user']
        
        token = attrs.get('token')
        backup_code = attrs.get('backup_code')
        
        if not token and not backup_code:
            raise serializers.ValidationError("Either 2FA token or backup code is required")
        
        if token and not user.verify_2fa_token(token):
            raise serializers.ValidationError("Invalid 2FA token")
        
        if backup_code and not user.verify_backup_code(backup_code):
            raise serializers.ValidationError("Invalid backup code")
        
        return attrs


class TwoFactorDisableSerializer(serializers.Serializer):
    """Serializer for disabling 2FA"""
    password = serializers.CharField(required=True)
    
    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password")
        return value
    
    def save(self):
        user = self.context['request'].user
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.two_factor_backup_codes = []
        user.save()
        
        return {'message': '2FA disabled successfully'}


class TwoFactorRegenerateBackupCodesSerializer(serializers.Serializer):
    """Serializer for regenerating backup codes"""
    password = serializers.CharField(required=True)
    
    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password")
        return value
    
    def save(self):
        user = self.context['request'].user
        backup_codes = user.generate_backup_codes()
        
        return {
            'message': 'Backup codes regenerated successfully',
            'backup_codes': backup_codes
        }
