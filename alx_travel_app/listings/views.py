import os
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import Booking, Payment
from .tasks import send_booking_confirmation_email

@require_http_methods(["POST"])
@csrf_exempt
def initiate_payment(request, booking_id):
    """
    Initiate payment with Chapa API
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Check if payment already exists
        if hasattr(booking, 'payment'):
            return JsonResponse({
                'error': 'Payment already initiated'
            }, status=400)
        
        # Prepare payment data for Chapa
        payment_data = {
            'amount': str(booking.total_price),
            'currency': 'ETB',
            'email': 'customer@example.com',
            'first_name': 'Customer',
            'last_name': 'User',
            'tx_ref': f'booking_{booking_id}',
            'return_url': 'http://localhost:8000/payment/success/',
        }
        
        # Make request to Chapa API
        headers = {
            'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{settings.CHAPA_BASE_URL}/transaction/initialize',
            json=payment_data,
            headers=headers
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Create payment record
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                status='pending',
                chapa_reference=response_data.get('data', {}).get('reference')
            )
            
            return JsonResponse({
                'success': True,
                'checkout_url': response_data['data']['checkout_url'],
                'message': 'Payment initiated successfully'
            })
        else:
            return JsonResponse({
                'error': 'Failed to initiate payment'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'error': f'Payment initiation failed: {str(e)}'
        }, status=500)

@require_http_methods(["GET", "POST"])
@csrf_exempt
def verify_payment(request, booking_id):
    """
    Verify payment status with Chapa API
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        payment = get_object_or_404(Payment, booking=booking)
        
        if payment.chapa_reference:
            headers = {
                'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
            }
            
            response = requests.get(
                f'{settings.CHAPA_BASE_URL}/transaction/verify/{payment.chapa_reference}/',
                headers=headers
            )
            
            if response.status_code == 200:
                verification_data = response.json()
                
                if verification_data['data']['status'] == 'success':
                    payment.status = 'completed'
                    payment.transaction_id = verification_data['data']['id']
                    payment.save()
                    
                    # 🚀 CELERY TASK: Send booking confirmation email
                    send_booking_confirmation_email.delay(booking.id)
                    
                    return JsonResponse({
                        'success': True,
                        'status': 'completed',
                        'message': 'Payment completed! Booking confirmation email is being sent.'
                    })
                else:
                    payment.status = 'failed'
                    payment.save()
                    
                    return JsonResponse({
                        'success': False,
                        'status': 'failed'
                    })
        
        return JsonResponse({
            'status': 'pending'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Payment verification failed: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def payment_status(request, booking_id):
    """
    Get current payment status
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        payment = get_object_or_404(Payment, booking=booking)
        
        return JsonResponse({
            'status': payment.status,
            'amount': str(payment.amount),
        })
        
    except Payment.DoesNotExist:
        return JsonResponse({
            'error': 'No payment found'
        }, status=404)
