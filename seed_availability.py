"""
Seed script to populate availability table with mock data for all providers
Creates availability records for upcoming dates with default time slots
"""

from datetime import datetime, timedelta
from database import Database
from config import Config
import sys

# Configure UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def seed_availability(days_ahead=30, start_date=None):
    """
    Create availability records for all providers for upcoming dates.
    
    Args:
        days_ahead: Number of days to create availability for (default: 30)
        start_date: Start date (datetime object). If None, starts from today.
    """
    
    # Initialize database
    try:
        db = Database()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure SUPABASE_URL and SUPABASE_KEY are set in .env")
        return
    
    # Get all active providers
    try:
        providers = db.get_providers(active_only=True)
        if not providers:
            print("No providers found. Please run seed_providers.py first.")
            return
        
        print(f"Found {len(providers)} active provider(s)")
    except Exception as e:
        print(f"Error getting providers: {e}")
        return
    
    # Determine start date
    if start_date is None:
        start_date = datetime.now().date()
    else:
        start_date = start_date.date() if isinstance(start_date, datetime) else start_date
    
    # Get default available times from config
    default_times = Config.DEFAULT_AVAILABLE_TIMES.copy()
    
    print(f"\nCreating availability for {days_ahead} days starting from {start_date}")
    print(f"Default time slots: {', '.join(default_times)}")
    print("-" * 60)
    
    total_created = 0
    total_skipped = 0
    
    # Create availability for each provider and date
    for provider in providers:
        provider_id = provider["provider_id"]
        provider_name = provider["name"]
        
        print(f"\nProcessing: {provider_name} ({provider_id})")
        
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")
            
            try:
                # Check if availability already exists
                try:
                    existing = db.client.table(db.table_availability)\
                        .select("*")\
                        .eq("provider_id", provider_id)\
                        .eq("date", date_str)\
                        .execute()
                    
                    # If it exists, skip it
                    if existing.data:
                        total_skipped += 1
                        continue
                except:
                    pass  # If check fails, try to create anyway
                
                # Create availability record
                db.create_availability(date_str, default_times, provider_id=provider_id)
                total_created += 1
                
                if day_offset < 3:  # Show first 3 days
                    print(f"  ✓ {date_str}: Created")
                
            except Exception as e:
                # If it already exists, that's fine - skip it
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    total_skipped += 1
                    continue
                else:
                    print(f"  ✗ {date_str}: Error - {e}")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Providers processed: {len(providers)}")
    print(f"Availability records created: {total_created}")
    print(f"Availability records skipped (already exist): {total_skipped}")
    print(f"Total date/provider combinations: {len(providers) * days_ahead}")
    print("\n✅ Availability seeding complete!")


def seed_specific_dates(provider_id=None, dates=None):
    """
    Create availability for specific dates and/or providers.
    
    Args:
        provider_id: Specific provider ID (if None, uses all providers)
        dates: List of date strings in YYYY-MM-DD format
    """
    try:
        db = Database()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return
    
    if dates is None:
        print("No dates provided")
        return
    
    if provider_id:
        providers = [{"provider_id": provider_id, "name": "Specified Provider"}]
    else:
        providers = db.get_providers(active_only=True)
    
    default_times = Config.DEFAULT_AVAILABLE_TIMES.copy()
    created = 0
    
    for provider in providers:
        for date_str in dates:
            try:
                db.create_availability(date_str, default_times, provider_id=provider["provider_id"])
                created += 1
                print(f"✓ Created availability for {provider['provider_id']} on {date_str}")
            except Exception as e:
                if "duplicate" in str(e).lower():
                    print(f"⊘ Skipped {provider['provider_id']} on {date_str} (already exists)")
                else:
                    print(f"✗ Error for {provider['provider_id']} on {date_str}: {e}")
    
    print(f"\nCreated {created} availability record(s)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed availability data for providers")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days ahead to create availability (default: 30)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date in YYYY-MM-DD format (default: today)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        help="Specific provider_id to seed (default: all providers)"
    )
    parser.add_argument(
        "--dates",
        nargs="+",
        help="Specific dates to seed in YYYY-MM-DD format"
    )
    
    args = parser.parse_args()
    
    if args.dates:
        # Seed specific dates
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
        seed_specific_dates(provider_id=args.provider, dates=args.dates)
    else:
        # Seed range of dates
        start_date = None
        if args.start_date:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        
        seed_availability(days_ahead=args.days, start_date=start_date)
