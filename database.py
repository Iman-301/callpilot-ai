"""
Database module for CallPilot using Supabase
Handles all database operations for availability and bookings
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, time as time_type
from supabase import create_client, Client
from config import Config
import os


class Database:
    """Supabase database client wrapper"""
    
    def __init__(self):
        """Initialize Supabase client"""
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.table_providers = "providers"
        self.table_availability = "availability"
        self.table_bookings = "bookings"
    
    def get_availability(self, date_str: str, provider_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get availability for a specific date and provider.
        If provider_id is None, returns aggregated availability across all providers.
        Creates default availability if date doesn't exist.
        
        Args:
            date_str: ISO format date string (YYYY-MM-DD)
            provider_id: Optional provider ID to filter by
        
        Returns:
            Dictionary with availability data
        """
        try:
            query = self.client.table(self.table_availability)\
                .select("*")\
                .eq("date", date_str)
            
            if provider_id:
                query = query.eq("provider_id", provider_id)
            
            response = query.execute()
            
            if response.data:
                if provider_id:
                    # Single provider
                    return {
                        "provider_id": response.data[0]["provider_id"],
                        "date": response.data[0]["date"],
                        "available_times": response.data[0]["available_times"] or [],
                        "booked_times": response.data[0]["booked_times"] or []
                    }
                else:
                    # Aggregate across all providers
                    all_available = set()
                    all_booked = set()
                    for item in response.data:
                        all_available.update(item["available_times"] or [])
                        all_booked.update(item["booked_times"] or [])
                    
                    return {
                        "date": date_str,
                        "available_times": sorted(list(all_available - all_booked)),
                        "booked_times": sorted(list(all_booked))
                    }
            else:
                # Create default availability
                if provider_id:
                    default_times = Config.DEFAULT_AVAILABLE_TIMES.copy()
                    return self.create_availability(date_str, default_times, provider_id)
                else:
                    return {
                        "date": date_str,
                        "available_times": Config.DEFAULT_AVAILABLE_TIMES.copy(),
                        "booked_times": []
                    }
        
        except Exception as e:
            print(f"Error getting availability: {e}")
            # Fallback to default
            return {
                "date": date_str,
                "available_times": Config.DEFAULT_AVAILABLE_TIMES.copy(),
                "booked_times": []
            }
    
    def create_availability(self, date_str: str, available_times: List[str], provider_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create availability record for a date and provider.
        
        Args:
            date_str: ISO format date string
            available_times: List of available time slots
            provider_id: Provider ID (if None, creates for a default provider)
        
        Returns:
            Created availability record
        """
        try:
            # If no provider_id, use a default or get first provider
            if not provider_id:
                providers = self.get_providers()
                if providers:
                    provider_id = providers[0]["provider_id"]
                else:
                    provider_id = "default"
            
            data = {
                "provider_id": provider_id,
                "date": date_str,
                "available_times": available_times,
                "booked_times": []
            }
            
            response = self.client.table(self.table_availability)\
                .insert(data)\
                .execute()
            
            return {
                "provider_id": response.data[0]["provider_id"],
                "date": response.data[0]["date"],
                "available_times": response.data[0]["available_times"] or [],
                "booked_times": response.data[0]["booked_times"] or []
            }
        except Exception as e:
            print(f"Error creating availability: {e}")
            # If it already exists, return existing
            return self.get_availability(date_str, provider_id)
    
    def book_time_slot(self, date_str: str, time: str, provider_id: Optional[str] = None) -> bool:
        """
        Book a time slot for a provider (add to booked_times array).
        
        Args:
            date_str: ISO format date string
            time: Time string in HH:MM format
            provider_id: Provider ID (if None, books for first available provider)
        
        Returns:
            True if successful
        """
        try:
            # Get current availability
            availability = self.get_availability(date_str, provider_id)
            
            if provider_id:
                booked_times = availability.get("booked_times", [])
                
                if time in booked_times:
                    return False  # Already booked
                
                # Add to booked_times
                booked_times.append(time)
                
                # Update in database
                self.client.table(self.table_availability)\
                    .update({"booked_times": booked_times})\
                    .eq("provider_id", provider_id)\
                    .eq("date", date_str)\
                    .execute()
            else:
                # Find first provider with available slot
                providers = self.get_providers()
                for provider in providers:
                    prov_avail = self.get_availability(date_str, provider["provider_id"])
                    if time not in prov_avail.get("booked_times", []):
                        booked_times = prov_avail.get("booked_times", [])
                        booked_times.append(time)
                        self.client.table(self.table_availability)\
                            .update({"booked_times": booked_times})\
                            .eq("provider_id", provider["provider_id"])\
                            .eq("date", date_str)\
                            .execute()
                        return True
                return False
            
            return True
        except Exception as e:
            print(f"Error booking time slot: {e}")
            return False
    
    def free_time_slot(self, date_str: str, time: str, provider_id: Optional[str] = None) -> bool:
        """
        Free a time slot for a provider (remove from booked_times array).
        
        Args:
            date_str: ISO format date string
            time: Time string in HH:MM format
            provider_id: Provider ID (if None, frees for all providers with that time)
        
        Returns:
            True if successful
        """
        try:
            if provider_id:
                # Get current availability for specific provider
                availability = self.get_availability(date_str, provider_id)
                booked_times = availability.get("booked_times", [])
                
                if time in booked_times:
                    booked_times.remove(time)
                    
                    # Update in database
                    self.client.table(self.table_availability)\
                        .update({"booked_times": booked_times})\
                        .eq("provider_id", provider_id)\
                        .eq("date", date_str)\
                        .execute()
            else:
                # Free for all providers
                providers = self.get_providers()
                for provider in providers:
                    prov_avail = self.get_availability(date_str, provider["provider_id"])
                    booked_times = prov_avail.get("booked_times", [])
                    if time in booked_times:
                        booked_times.remove(time)
                        self.client.table(self.table_availability)\
                            .update({"booked_times": booked_times})\
                            .eq("provider_id", provider["provider_id"])\
                            .eq("date", date_str)\
                            .execute()
            
            return True
        except Exception as e:
            print(f"Error freeing time slot: {e}")
            return False
    
    def create_booking(self, confirmation_id: str, date_str: str, time: str, 
                      service: str, provider_id: Optional[str] = None,
                      phone_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a booking record.
        
        Args:
            confirmation_id: Unique confirmation ID
            date_str: ISO format date string
            time: Time string in HH:MM format
            service: Service type
            provider_id: Provider ID (if None, finds first available provider)
            phone_number: Optional phone number
        
        Returns:
            Created booking record
        """
        try:
            # If no provider_id, find first available provider for this service
            if not provider_id:
                providers = self.get_providers_by_service(service)
                if providers:
                    provider_id = providers[0]["provider_id"]
                else:
                    provider_id = "default"
            
            data = {
                "confirmation_id": confirmation_id,
                "provider_id": provider_id,
                "date": date_str,
                "time": time,
                "service": service,
                "status": "confirmed",
                "phone_number": phone_number
            }
            
            response = self.client.table(self.table_bookings)\
                .insert(data)\
                .execute()
            
            return response.data[0]
        except Exception as e:
            print(f"Error creating booking: {e}")
            raise
    
    def get_booking(self, confirmation_id: Optional[str] = None, 
                   phone_number: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a booking by confirmation ID or phone number.
        
        Args:
            confirmation_id: Confirmation ID to search for
            phone_number: Phone number to search for
        
        Returns:
            Booking record or None
        """
        try:
            if confirmation_id:
                response = self.client.table(self.table_bookings)\
                    .select("*")\
                    .eq("confirmation_id", confirmation_id)\
                    .execute()
                
                if response.data:
                    return response.data[0]
            
            if phone_number:
                response = self.client.table(self.table_bookings)\
                    .select("*")\
                    .eq("phone_number", phone_number)\
                    .eq("status", "confirmed")\
                    .order("created_at", desc=True)\
                    .limit(1)\
                    .execute()
                
                if response.data:
                    return response.data[0]
            
            return None
        except Exception as e:
            print(f"Error getting booking: {e}")
            return None
    
    def update_booking_status(self, confirmation_id: str, status: str) -> bool:
        """
        Update booking status (confirmed, rescheduled, cancelled).
        
        Args:
            confirmation_id: Confirmation ID
            status: New status
        
        Returns:
            True if successful
        """
        try:
            self.client.table(self.table_bookings)\
                .update({"status": status})\
                .eq("confirmation_id", confirmation_id)\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error updating booking status: {e}")
            return False
    
    def update_booking_datetime(self, confirmation_id: str, new_date: str, new_time: str, new_provider_id: Optional[str] = None) -> bool:
        """
        Update booking date and time (for rescheduling).
        
        Args:
            confirmation_id: Confirmation ID
            new_date: New date in ISO format
            new_time: New time in HH:MM format
            new_provider_id: Optional new provider ID
        
        Returns:
            True if successful
        """
        try:
            update_data = {
                "date": new_date,
                "time": new_time,
                "status": "rescheduled"
            }
            
            if new_provider_id:
                update_data["provider_id"] = new_provider_id
            
            self.client.table(self.table_bookings)\
                .update(update_data)\
                .eq("confirmation_id", confirmation_id)\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error updating booking datetime: {e}")
            return False
    
    def get_providers(self, service: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of providers, optionally filtered by service.
        
        Args:
            service: Optional service type to filter by
            active_only: Only return active providers
        
        Returns:
            List of provider records
        """
        try:
            query = self.client.table(self.table_providers).select("*")
            
            if service:
                query = query.eq("service", service)
            
            if active_only:
                query = query.eq("active", True)
            
            response = query.execute()
            return response.data or []
        except Exception as e:
            print(f"Error getting providers: {e}")
            return []
    
    def get_providers_by_service(self, service: str) -> List[Dict[str, Any]]:
        """
        Get providers for a specific service.
        
        Args:
            service: Service type
        
        Returns:
            List of provider records
        """
        return self.get_providers(service=service, active_only=True)
    
    def create_provider(self, provider_id: str, name: str, service: str,
                       phone_number: Optional[str] = None, email: Optional[str] = None,
                       rating: Optional[float] = None, distance_km: Optional[float] = None,
                       metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a new provider.
        
        Args:
            provider_id: Unique provider identifier
            name: Provider name
            service: Service type
            phone_number: Optional phone number
            email: Optional email
            rating: Optional rating
            distance_km: Optional distance
            metadata: Optional metadata JSON
        
        Returns:
            Created provider record
        """
        try:
            data = {
                "provider_id": provider_id,
                "name": name,
                "service": service,
                "phone_number": phone_number,
                "email": email,
                "rating": rating,
                "distance_km": distance_km,
                "metadata": metadata,
                "active": True
            }
            
            response = self.client.table(self.table_providers)\
                .insert(data)\
                .execute()
            
            return response.data[0]
        except Exception as e:
            print(f"Error creating provider: {e}")
            raise


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get or create database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db
