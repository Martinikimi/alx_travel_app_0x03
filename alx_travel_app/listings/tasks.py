from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_booking_confirmation_email(booking_id):
    """
    Send booking confirmation email as a background task
    """
    try:
        # Import here to avoid circular imports
        from .models import Booking
        
        # Get the booking object
        booking = Booking.objects.get(id=booking_id)
        
        # Email content
        subject = f'Booking Confirmation - #{booking.id}'
        message = f"""
        Hello {booking.user.username if booking.user else 'Guest'},

        Your booking has been confirmed!

        Booking Details:
        - Booking ID: {booking.id}
        - Property: {booking.listing.title}
        - Check-in: {booking.check_in_date}
        - Check-out: {booking.check_out_date}
        - Total Guests: {booking.guests}
        - Total Price: ${booking.total_price}

        Thank you for choosing our service!

        Best regards,
        ALX Travel Team
        """
        
        # Determine recipient email
        if booking.user and booking.user.email:
            recipient_email = booking.user.email
        else:
            # Fallback for guest bookings
            recipient_email = booking.guest_email if hasattr(booking, 'guest_email') else 'guest@example.com'
        
        # Send the email
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        # Log success
        logger.info(f"Booking confirmation email sent for booking #{booking_id} to {recipient_email}")
        
        return f"Email sent successfully to {recipient_email}"
        
    except Exception as e:
        # Log error
        logger.error(f"Failed to send booking confirmation email for booking #{booking_id}: {str(e)}")
        return f"Error: {str(e)}"