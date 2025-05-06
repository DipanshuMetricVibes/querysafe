def get_registration_redirect(user):
    """Determine where to redirect user based on registration status"""
    if user.registration_status == 'registered':
        return 'verify_otp', 'Please verify your email first.'
    elif user.registration_status == 'otp_verified' or not user.is_active:
        return 'verify_activation', 'Please activate your account.'
    return None, None