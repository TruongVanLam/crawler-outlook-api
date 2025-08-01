"""
Auto sync service for automatically syncing emails when new accounts are created
"""
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .services import EmailSyncService
from .meta_receipt_service import MetaReceiptService
from .auth import refresh_access_token
from database import get_db
from models import Account, AuthToken


class AutoSyncService:
    """Service for automatically syncing emails for new accounts"""
    
    def __init__(self):
        self.is_running = False
        self.sync_thread = None
        self.sync_interval = 60  # 1 minute - check for new day
        self.new_accounts = set()  # Track new accounts that need initial sync
        self.last_daily_sync_date = None  # Track last daily sync date
    
    def start_auto_sync(self):
        """Start the auto sync service"""
        if self.is_running:
            print("Auto sync service is already running")
            return
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        print("Auto sync service started")
    
    def stop_auto_sync(self):
        """Stop the auto sync service"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join()
        print("Auto sync service stopped")
    
    def add_new_account(self, account_id: int):
        """Add a new account to the sync queue"""
        self.new_accounts.add(account_id)
        print(f"Added account {account_id} to auto sync queue")
    
    def _sync_loop(self):
        """Main sync loop that runs in background thread"""
        while self.is_running:
            try:
                self._process_new_accounts()
                self._check_and_process_daily_sync()
                time.sleep(self.sync_interval)
            except Exception as e:
                print(f"Error in auto sync loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _process_new_accounts(self):
        """Process new accounts that need initial sync"""
        if not self.new_accounts:
            return
        
        db = next(get_db())
        try:
            for account_id in list(self.new_accounts):
                try:
                    print(f"Processing initial sync for account {account_id}")
                    
                    # Check if account exists and has valid token
                    account = db.query(Account).filter_by(id=account_id, is_active=True).first()
                    if not account:
                        print(f"Account {account_id} not found or inactive")
                        self.new_accounts.discard(account_id)
                        continue
                    
                    # Check if account has valid auth token and refresh if needed
                    auth_token = db.query(AuthToken).filter(
                        and_(
                            AuthToken.account_id == account_id,
                            AuthToken.is_active == True
                        )
                    ).first()
                    
                    if not auth_token:
                        print(f"Account {account_id} has no auth token")
                        self.new_accounts.discard(account_id)
                        continue
                    
                    # Check if token is expired and refresh if needed
                    if auth_token.expires_at <= datetime.utcnow():
                        print(f"🔄 Token expired for account {account_id}, refreshing...")
                        try:
                            refresh_access_token(db, account_id)
                            print(f"✅ Token refreshed for account {account_id}")
                        except Exception as e:
                            print(f"❌ Failed to refresh token for account {account_id}: {str(e)}")
                            self.new_accounts.discard(account_id)
                            continue
                    
                    # Perform initial monthly sync
                    sync_service = EmailSyncService(db, account_id)
                    result = sync_service.sync_monthly_emails()
                    
                    print(f"Initial sync completed for account {account_id}: {result['total_synced']} emails synced")
                    
                    # Process meta receipts
                    meta_service = MetaReceiptService(db)
                    meta_result = meta_service.process_account(account_id)
                    
                    print(f"Meta receipts processed for account {account_id}: {meta_result['processed_count']} receipts")
                    
                    # Remove from new accounts set
                    self.new_accounts.discard(account_id)
                    
                except Exception as e:
                    print(f"Error processing account {account_id}: {str(e)}")
                    # Keep in new_accounts set for retry
                    continue
                    
        except Exception as e:
            print(f"Error in _process_new_accounts: {str(e)}")
        finally:
            db.close()
    
    def _check_and_process_daily_sync(self):
        """Check if it's a new day and process daily sync once per day"""
        current_date = datetime.utcnow().date()
        
        # If we haven't done daily sync today, do it
        if self.last_daily_sync_date != current_date:
            print(f"🔄 Starting daily sync for date: {current_date}")
            self._process_daily_sync()
            self.last_daily_sync_date = current_date
            print(f"✅ Daily sync completed for date: {current_date}")
    
    def _process_daily_sync(self):
        """Process daily sync for all active accounts (runs once per day)"""
        db = next(get_db())
        try:
            # Get all active accounts with tokens (we'll refresh expired ones)
            active_accounts = db.query(Account).join(AuthToken).filter(
                and_(
                    Account.is_active == True,
                    AuthToken.is_active == True
                )
            ).all()
            
            total_accounts = len(active_accounts)
            processed_accounts = 0
            total_emails_synced = 0
            total_receipts_processed = 0
            
            print(f"📊 Processing daily sync for {total_accounts} active accounts")
            
            for account in active_accounts:
                try:
                    # Check if account needs daily sync (not in new_accounts)
                    if account.id in self.new_accounts:
                        print(f"⏭️ Skipping account {account.id} (in new accounts queue)")
                        continue
                    
                    print(f"📧 Processing daily sync for account {account.id} ({account.email})")
                    
                    # Check if token is expired and refresh if needed
                    auth_token = db.query(AuthToken).filter(
                        and_(
                            AuthToken.account_id == account.id,
                            AuthToken.is_active == True
                        )
                    ).first()
                    
                    if auth_token and auth_token.expires_at <= datetime.utcnow():
                        print(f"🔄 Token expired for account {account.id}, refreshing...")
                        try:
                            refresh_access_token(db, account.id)
                            print(f"✅ Token refreshed for account {account.id}")
                        except Exception as e:
                            print(f"❌ Failed to refresh token for account {account.id}: {str(e)}")
                            continue
                    
                    # Perform daily sync with max 999 emails
                    sync_service = EmailSyncService(db, account.id)
                    result = sync_service.sync_daily_emails()
                    
                    emails_synced = result['total_synced']
                    total_emails_synced += emails_synced
                    
                    if emails_synced > 0:
                        print(f"✅ Daily sync completed for account {account.id}: {emails_synced} new emails")
                        
                        # Process new meta receipts
                        meta_service = MetaReceiptService(db)
                        meta_result = meta_service.process_account(account.id)
                        
                        receipts_processed = meta_result['processed_count']
                        total_receipts_processed += receipts_processed
                        
                        if receipts_processed > 0:
                            print(f"📄 Meta receipts processed for account {account.id}: {receipts_processed} receipts")
                    else:
                        print(f"ℹ️ No new emails for account {account.id}")
                    
                    processed_accounts += 1
                    
                except Exception as e:
                    print(f"❌ Error processing daily sync for account {account.id}: {str(e)}")
                    continue
            
            print(f"📈 Daily sync summary: {processed_accounts}/{total_accounts} accounts processed")
            print(f"📧 Total emails synced: {total_emails_synced}")
            print(f"📄 Total receipts processed: {total_receipts_processed}")
                    
        except Exception as e:
            print(f"❌ Error in _process_daily_sync: {str(e)}")
        finally:
            db.close()
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync service status"""
        return {
            "is_running": self.is_running,
            "sync_interval": self.sync_interval,
            "new_accounts_count": len(self.new_accounts),
            "new_accounts": list(self.new_accounts)
        }


# Global instance
auto_sync_service = AutoSyncService() 