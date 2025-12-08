#!/usr/bin/env python3
"""
Create a user account via the authentication API.

This utility script provides a convenient way to create user accounts
for testing and development purposes.
"""
import requests
import json
import sys


def create_user(username, email, password, org_name=None):
    """
    Create a user account via the signup API endpoint.
    
    Args:
        username: Username for the new account
        email: Email address for the new account
        password: Password for the new account
        org_name: Optional organization name
        
    Returns:
        dict: Response data from the API
        
    Raises:
        SystemExit: If the API request fails
    """
    url = "http://localhost:4000/auth/signup"
    data = {
        "username": username,
        "email": email,
        "password": password,
    }
    
    if org_name:
        data["orgName"] = org_name
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        
        print("User created successfully!")
        print(json.dumps(result, indent=2))
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error creating user: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except Exception:
                print(f"Status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-user.py <username> <email> <password> [org_name]")
        print("\nExample:")
        print("  python create-user.py john_doe john@example.com mypassword123 'My Company'")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    org_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    create_user(username, email, password, org_name)

