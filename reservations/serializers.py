from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from properties.models import Property, Room, RoomCategory, RoomAvailability
from properties.utils import convert_r2_url_to_public
from .models import Reservation, Payment, Refund, Cancellation, BookingModification, CheckIn, CheckOut, ReviewInvitation

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = '__all__'


class CancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cancellation
        fields = '__all__'


class BookingModificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingModification
        fields = '__all__'


class CheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckIn
        fields = '__all__'


class CheckOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckOut
        fields = '__all__'


class ReviewInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewInvitation
        fields = '__all__'


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['id', 'reference']


class ReservationCreateSerializer(serializers.ModelSerializer):
    room_category_id = serializers.IntegerField(write_only=True, required=False)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(), required=False)
    room_category = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Reservation
        fields = ('property_obj', 'room', 'room_category', 'room_category_id', 'check_in', 'check_out', 'guests',
                  'guest_first_name', 'guest_last_name', 'guest_email', 'guest_phone',
                  'payment_method', 'special_requests', 'estimated_arrival_time', 'flight_details')

    def validate(self, attrs):
        print("[ReservationCreateSerializer.validate] raw attrs keys:", list(attrs.keys()))
        try:
            snapshot = {k: (str(v) if v is not None else None) for k, v in attrs.items()}
            print("[ReservationCreateSerializer.validate] attrs snapshot:", snapshot)
        except Exception as e:
            print("[ReservationCreateSerializer.validate] snapshot error:", e)
        check_in = attrs['check_in']
        check_out = attrs['check_out']
        guests = attrs['guests']
        print(f"[ReservationCreateSerializer.validate] check_in={check_in}, check_out={check_out}, guests={guests}, payment_method={attrs.get('payment_method')}")

        # Validate dates
        if check_in >= check_out:
            raise serializers.ValidationError("Check-out date must be after check-in date")

        if check_in < timezone.now().date():
            raise serializers.ValidationError("Check-in date cannot be in the past")

        # Handle room assignment
        if 'room' in attrs and 'room_category_id' not in attrs:
            room = attrs['room']
            # Validate room capacity (skip for pay on arrival)
            if attrs.get('payment_method') != 'pay_on_arrival':
                try:
                    if guests > room.max_guests:
                        raise serializers.ValidationError(f"Room can only accommodate {room.max_guests} guests")
                except AttributeError:
                    # If room doesn't have max_guests, skip this validation
                    pass

            # Check availability - skip for pay now since it's immediate payment
            if attrs.get('payment_method') != 'pay_now':
                conflicting_reservations = Reservation.objects.filter(
                    room=room,
                    status__in=['confirmed'],
                    check_in__lt=check_out,
                    check_out__gt=check_in
                )

                if conflicting_reservations.exists():
                    raise serializers.ValidationError("Room is not available for the selected dates")
        elif 'room_category_id' in attrs:
            # Remove room if category is provided to avoid conflicts
            if 'room' in attrs:
                del attrs['room']
            # Find an available room for this category
            room_category_id = attrs['room_category_id']
            if not room_category_id:
                raise serializers.ValidationError("Room category is required")
            try:
                room_category = RoomCategory.objects.get(id=room_category_id)
                try:
                    print(f"[ReservationCreateSerializer.validate] room_category_id={room_category_id}, name={room_category.name}, rooms={room_category.rooms.count()}")
                except Exception as e:
                    print("[ReservationCreateSerializer.validate] error logging room_category:", e)

                # Find available rooms in this category
                available_rooms = []
                preferred_rooms = []
                for room in room_category.rooms.all():
                    # Check for conflicting reservations
                    conflicting_reservations = Reservation.objects.filter(
                        room=room,
                        status__in=['confirmed'],
                        check_in__lt=check_out,
                        check_out__gt=check_in
                    )

                    # Check room availability calendar
                    unavailable_dates = RoomAvailability.objects.filter(
                        room=room,
                        date__gte=check_in,
                        date__lt=check_out,
                        available=False
                    )

                    if not conflicting_reservations.exists() and not unavailable_dates.exists() and guests <= room.max_guests:
                        available_rooms.append(room)
                        # Prefer room with type matching category name
                        if room.type == room_category.name:
                            preferred_rooms.append(room)

                print(f"[ReservationCreateSerializer.validate] available_rooms={len(available_rooms)}, preferred_rooms={len(preferred_rooms)}")
                if not available_rooms:
                    raise serializers.ValidationError("No rooms available in this category for the selected dates")

                # Use preferred room if available, otherwise any available room from the category
                selected_room = preferred_rooms[0] if preferred_rooms else available_rooms[0]
                try:
                    print(f"[ReservationCreateSerializer.validate] selected_room_id={selected_room.id}, selected_room_name={selected_room.name}")
                except Exception as e:
                    print("[ReservationCreateSerializer.validate] error logging selected_room:", e)
                attrs['room'] = selected_room
                attrs['room_category'] = room_category
            except RoomCategory.DoesNotExist:
                raise serializers.ValidationError("Room category not found")
            except Exception as e:
                print(f"Error in room_category_id validation: {e}")
                raise serializers.ValidationError(f"Error finding available room: {str(e)}")

        return attrs

    def create(self, validated_data):
        print("[ReservationCreateSerializer.create] entering with keys:", list(validated_data.keys()))
        user = self.context['request'].user
        room = validated_data.get('room')
        # Remove write-only helper so model init doesn't receive unexpected kwargs
        room_category_id = validated_data.pop('room_category_id', None)
        print(f"[ReservationCreateSerializer.create] popped room_category_id={room_category_id}, room_id={getattr(room, 'id', None)}")
        check_in = validated_data['check_in']
        check_out = validated_data['check_out']
        guests = validated_data['guests']

        # Calculate total price
        nights = (check_out - check_in).days
        total_price = 0

        # Use category base price for total calculation if category was used
        if room_category_id:
            try:
                rc = RoomCategory.objects.get(id=room_category_id)
                total_price = rc.base_price * nights
                print(f"[ReservationCreateSerializer.create] pricing via category base_price={rc.base_price} nights={nights}")
            except RoomCategory.DoesNotExist:
                # Fallback to room price if available
                if room:
                    total_price = room.price_per_night * nights
                    print(f"[ReservationCreateSerializer.create] fallback pricing via room price_per_night={room.price_per_night} nights={nights}")
                else:
                    print("[ReservationCreateSerializer.create] invalid room_category_id and no room provided")
                    raise serializers.ValidationError("Invalid room category specified")
        else:
            if not room:
                print("[ReservationCreateSerializer.create] missing room and no category provided")
                raise serializers.ValidationError("Room must be specified")
            total_price = room.price_per_night * nights
            print(f"[ReservationCreateSerializer.create] pricing via room price_per_night={room.price_per_night} nights={nights}")

        validated_data['user'] = user
        validated_data['total_price'] = total_price

        # Auto-confirm pay on arrival reservations
        if validated_data.get('payment_method') == 'pay_on_arrival':
            print("[ReservationCreateSerializer.create] payment_method=pay_on_arrival -> set status=confirmed")
            validated_data['status'] = 'confirmed'

        # Generate unique reference
        import random
        while True:
            reference = f"RWE{random.randint(1000000, 9999999)}"
            if not Reservation.objects.filter(reference=reference).exists():
                break
        validated_data['reference'] = reference
        print("[ReservationCreateSerializer.create] final validated_data keys:", list(validated_data.keys()))
        print("[ReservationCreateSerializer.create] total_price=", total_price)
        return super().create(validated_data)


class ReservationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ('check_in', 'check_out', 'guests', 'total_price', 'status', 'special_requests',
                 'estimated_arrival_time', 'flight_details', 'payment_status', 'amount_paid',
                 'payment_date', 'collected_by', 'payment_notes')


class ReservationListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property_obj.name', read_only=True)
    property_city = serializers.CharField(source='property_obj.city', read_only=True)
    property_location = serializers.SerializerMethodField()
    property_image = serializers.SerializerMethodField()
    property_rating = serializers.FloatField(source='property_obj.rating', read_only=True)
    property_review_count = serializers.IntegerField(source='property_obj.review_count', read_only=True)
    property_owner = serializers.SerializerMethodField()
    room_name = serializers.SerializerMethodField()
    room_type = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    nights = serializers.ReadOnlyField()
    is_paid = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    receipt_url = serializers.SerializerMethodField()
    download_receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = ('id', 'property_obj', 'property_name', 'property_city', 'property_location', 'property_image', 'property_rating', 'property_review_count', 'property_owner',
                 'room', 'room_name', 'room_type', 'user', 'user_name', 'check_in', 'check_out', 'guests', 'total_price',
                 'status', 'payment_method', 'payment_status', 'amount_paid', 'created_at', 'nights', 'is_paid', 'is_active',
                 'receipt_url', 'download_receipt_url')

    def get_receipt_url(self, obj):
        if obj.payment_receipt:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.payment_receipt.url)
            return obj.payment_receipt.url
        return None

    def get_download_receipt_url(self, obj):
        if obj.payment_receipt:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f"/api/reservations/{obj.id}/download-receipt/")
            return f"/api/reservations/{obj.id}/download-receipt/"
        return None

    def get_property_owner(self, obj):
        owner = obj.property_obj.owner
        return {
            'id': owner.id,
            'username': owner.username,
            'get_full_name': owner.get_full_name(),
            'profile_picture': owner.profile_picture.url if owner.profile_picture else None,
        }

    def get_property_location(self, obj):
        return f"{obj.property_obj.city}, {obj.property_obj.country}"

    def get_property_image(self, obj):
        try:
            imgs = obj.property_obj.images or []
            if imgs:
                return convert_r2_url_to_public(imgs[0])
            return None
        except Exception:
            return None

    def get_room_name(self, obj):
        if obj.room_category:
            return obj.room_category.name
        return obj.room.name if obj.room else ''

    def get_room_type(self, obj):
        if obj.room_category:
            return obj.room_category.name  # or some type field
        return obj.room.type if obj.room else ''


class OwnerReservationSerializer(serializers.ModelSerializer):
    property = serializers.IntegerField(source='property_obj.id', read_only=True)
    property_name = serializers.CharField(source='property_obj.name', read_only=True)
    property_location = serializers.SerializerMethodField()
    property_image = serializers.SerializerMethodField()
    guest_info = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    guest_name = serializers.SerializerMethodField()
    room_name = serializers.SerializerMethodField()
    owner_user_id = serializers.IntegerField(source='property_obj.owner.id', read_only=True)

    class Meta:
        model = Reservation
        fields = ('id', 'property', 'property_name', 'property_location', 'property_image',
                 'user', 'room', 'room_name', 'check_in', 'check_out', 'guests', 'total_price', 'status', 'payment_status',
                 'created_at', 'updated_at', 'guest_info', 'payment', 'guest_name', 'reference', 'owner_user_id')

    def get_property_location(self, obj):
        return f"{obj.property_obj.city}, {obj.property_obj.country}"

    def get_property_image(self, obj):
        # Property.images is a JSONField containing list of image URLs
        if obj.property_obj.images and len(obj.property_obj.images) > 0:
            # Return the first image URL converted to public format
            return convert_r2_url_to_public(obj.property_obj.images[0])
        return None

    def get_guest_info(self, obj):
        return {
            'first_name': obj.guest_first_name,
            'last_name': obj.guest_last_name,
            'email': obj.guest_email,
            'phone': obj.guest_phone
        }

    def get_payment(self, obj):
        return {
            'method': obj.payment_method,
            'status': obj.payment_status,
            'amount_paid': float(obj.amount_paid or 0),
            'payment_date': obj.payment_date.isoformat() if obj.payment_date else None,
            'collected_by': obj.collected_by
        }

    def get_guest_name(self, obj):
        return f"{obj.guest_first_name} {obj.guest_last_name}"

    def get_room_name(self, obj):
        if obj.room_category:
            return obj.room_category.name
        return obj.room.name if obj.room else ''


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('payment_type', 'payment_method', 'amount', 'transaction_id', 'gateway_response')

    def create(self, validated_data):
        reservation_id = self.context['reservation_id']
        # Get the reservation object
        from .models import Reservation
        reservation = Reservation.objects.get(id=reservation_id)
        validated_data['reservation'] = reservation
        return super().create(validated_data)


class CancellationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cancellation
        fields = ('reason', 'reason_details')

    def create(self, validated_data):
        reservation = self.context['reservation']
        validated_data['reservation'] = reservation
        validated_data['processed_by'] = self.context['request'].user
        
        # Update reservation status
        reservation.status = 'cancelled'
        reservation.save()
        
        return super().create(validated_data)


class CheckInCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckIn
        fields = ('actual_check_in_time', 'notes', 'id_document_verified', 'payment_collected')

    def create(self, validated_data):
        reservation = self.context['reservation']
        validated_data['reservation'] = reservation
        validated_data['checked_in_by'] = self.context['request'].user
        return super().create(validated_data)


class CheckOutCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckOut
        fields = ('actual_check_out_time', 'notes', 'additional_charges', 'damage_charges')

    def create(self, validated_data):
        reservation = self.context['reservation']
        validated_data['reservation'] = reservation
        validated_data['checked_out_by'] = self.context['request'].user
        
        # Update reservation status
        reservation.status = 'completed'
        reservation.save()
        
        return super().create(validated_data)
