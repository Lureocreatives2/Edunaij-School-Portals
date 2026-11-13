"""
Domain validation and DNS verification services for EduNaija.

Handles:
- CNAME record validation
- TXT record validation
- DNS challenge token generation
- Domain ownership verification
"""

import dns.resolver
import dns.exception
import secrets
import hashlib
from typing import Tuple, Dict, Optional
from datetime import timedelta
from django.utils import timezone

from .models import TenantDomain, Tenant


def generate_dns_challenge_token() -> str:
    """
    Generate a secure DNS challenge token for domain verification.
    
    Returns:
        A 32-character random token
    """
    return secrets.token_hex(16)


def get_cname_challenge_record(domain: str, subdomain: str) -> str:
    """
    Generate the CNAME record that should point to the platform.
    
    Args:
        domain: The custom domain (e.g., 'school.edu.ng')
        subdomain: The school's platform subdomain (e.g., 'alpha-school')
    
    Returns:
        The full CNAME target (e.g., 'alpha-school.edunaija.com')
    """
    # Platform root domain - in production, configure via settings
    platform_root = 'edunaija.com'
    return f"{subdomain}.{platform_root}"


def get_txt_challenge_record(token: str) -> str:
    """
    Generate the TXT record value for DNS verification.
    
    Args:
        token: The DNS challenge token
    
    Returns:
        The TXT record value
    """
    return f"edunaija-verify={token}"


def verify_cname_record(domain: str, expected_target: str) -> Tuple[bool, str]:
    """
    Verify that a custom domain has the correct CNAME record pointing to the platform.
    
    Args:
        domain: The custom domain to verify
        expected_target: The expected CNAME target
    
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        answers = dns.resolver.resolve(domain, 'CNAME', lifetime=10)
        
        for rdata in answers:
            cname_target = str(rdata.target).rstrip('.')
            if cname_target.lower() == expected_target.lower():
                return True, f"CNAME record verified for {domain}"
        
        actual_targets = ', '.join([str(r.target).rstrip('.') for r in answers])
        return False, f"CNAME mismatch. Found: {actual_targets}, Expected: {expected_target}"
    
    except dns.resolver.NXDOMAIN:
        return False, f"Domain {domain} does not exist (NXDOMAIN)"
    except dns.resolver.NoAnswer:
        return False, f"No CNAME record found for {domain}"
    except dns.exception.Timeout:
        return False, f"DNS query timed out for {domain}"
    except Exception as e:
        return False, f"DNS verification error: {str(e)}"


def verify_txt_record(domain: str, expected_token: str) -> Tuple[bool, str]:
    """
    Verify that a custom domain has the correct TXT record for ownership verification.
    
    Args:
        domain: The custom domain to verify
        expected_token: The expected verification token
    
    Returns:
        Tuple of (is_valid, message)
    """
    expected_txt = get_txt_challenge_record(expected_token)
    
    try:
        answers = dns.resolver.resolve(domain, 'TXT', lifetime=10)
        
        for rdata in answers:
            for text in rdata.strings:
                txt_value = text.decode('utf-8')
                if txt_value == expected_txt:
                    return True, f"TXT record verified for {domain}"
        
        found_records = []
        for rdata in answers:
            for text in rdata.strings:
                found_records.append(text.decode('utf-8'))
        
        return False, (
            f"TXT record mismatch. Expected: {expected_txt}, "
            f"Found: {', '.join(found_records) if found_records else 'none'}"
        )
    
    except dns.resolver.NXDOMAIN:
        return False, f"Domain {domain} does not exist (NXDOMAIN)"
    except dns.resolver.NoAnswer:
        return False, f"No TXT record found for {domain}. Expected: {expected_txt}"
    except dns.exception.Timeout:
        return False, f"DNS query timed out for {domain}"
    except Exception as e:
        return False, f"DNS verification error: {str(e)}"


def verify_domain_ownership(tenant_domain: TenantDomain) -> Tuple[bool, str]:
    """
    Verify domain ownership based on the configured verification method.
    
    Args:
        tenant_domain: The TenantDomain instance to verify
    
    Returns:
        Tuple of (is_valid, message)
    """
    if tenant_domain.verification_status == 'verified':
        return True, "Domain already verified"
    
    if tenant_domain.verification_method == 'cname':
        expected_cname = get_cname_challenge_record(
            tenant_domain.domain,
            tenant_domain.tenant.subdomain
        )
        is_valid, message = verify_cname_record(tenant_domain.domain, expected_cname)
    
    elif tenant_domain.verification_method == 'txt':
        if not tenant_domain.dns_challenge_token:
            return False, "DNS challenge token not set"
        is_valid, message = verify_txt_record(
            tenant_domain.domain,
            tenant_domain.dns_challenge_token
        )
    
    else:
        return False, f"Unknown verification method: {tenant_domain.verification_method}"
    
    if is_valid:
        tenant_domain.verification_status = 'verified'
        tenant_domain.verified_at = timezone.now()
    else:
        tenant_domain.verification_status = 'failed'
    
    tenant_domain.last_verification_check = timezone.now()
    tenant_domain.save()
    
    return is_valid, message


def prepare_domain_verification(
    tenant: Tenant,
    domain: str,
    verification_method: str = 'cname'
) -> Dict[str, str]:
    """
    Prepare a domain for verification by setting up challenge records.
    
    Args:
        tenant: The Tenant instance
        domain: The custom domain
        verification_method: 'cname' or 'txt'
    
    Returns:
        Dict with verification instructions
    """
    tenant_domain, _ = TenantDomain.objects.get_or_create(
        tenant=tenant,
        domain=domain,
        defaults={
            'verification_status': 'pending',
            'verification_method': verification_method
        }
    )
    
    if verification_method == 'txt':
        if not tenant_domain.dns_challenge_token:
            tenant_domain.dns_challenge_token = generate_dns_challenge_token()
            tenant_domain.dns_challenge_type = 'TXT'
            tenant_domain.save()
        
        return {
            'domain': domain,
            'method': 'txt',
            'record_type': 'TXT',
            'record_name': domain,
            'record_value': get_txt_challenge_record(tenant_domain.dns_challenge_token),
            'instructions': (
                f'Add a TXT record to {domain}:\n'
                f'Name: {domain}\n'
                f'Type: TXT\n'
                f'Value: {get_txt_challenge_record(tenant_domain.dns_challenge_token)}'
            )
        }
    
    else:  # cname
        cname_target = get_cname_challenge_record(domain, tenant.subdomain)
        tenant_domain.dns_challenge_type = 'CNAME'
        tenant_domain.save()
        
        return {
            'domain': domain,
            'method': 'cname',
            'record_type': 'CNAME',
            'record_name': domain,
            'record_value': cname_target,
            'instructions': (
                f'Add a CNAME record to {domain}:\n'
                f'Name: {domain}\n'
                f'Type: CNAME\n'
                f'Value: {cname_target}'
            )
        }


def get_domain_verification_status(tenant_domain: TenantDomain) -> Dict:
    """
    Get the current verification status and instructions for a domain.
    
    Args:
        tenant_domain: The TenantDomain instance
    
    Returns:
        Dict with status and instructions
    """
    status = {
        'domain': tenant_domain.domain,
        'verification_status': tenant_domain.verification_status,
        'verification_method': tenant_domain.verification_method,
        'is_verified': tenant_domain.is_verified(),
        'last_check': tenant_domain.last_verification_check,
    }
    
    if tenant_domain.verification_method == 'cname':
        status['expected_cname'] = get_cname_challenge_record(
            tenant_domain.domain,
            tenant_domain.tenant.subdomain
        )
    elif tenant_domain.verification_method == 'txt':
        status['expected_txt'] = get_txt_challenge_record(
            tenant_domain.dns_challenge_token
        )
    
    return status
