#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Timestamp Errors Script
---------------------------
This script fixes timestamp field type errors in Firestore documents.
It updates documents that have incorrect timestamp types to use SERVER_TIMESTAMP.
"""

import os
import json
import logging
from pathlib import Path
from typing import List

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()

# Configuration
FIREBASE_CREDENTIALS = os.environ["FIREBASE_CREDENTIALS"]

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

def initialize_firebase():
    """Initialize Firebase connection."""
    try:
        if os.path.isfile(FIREBASE_CREDENTIALS):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS)
            log.info("Firebase-Credentials loaded from file.")
        else:
            cred_dict = json.loads(FIREBASE_CREDENTIALS)
            cred = credentials.Certificate(cred_dict)
            log.info("Firebase-Credentials loaded from JSON string.")
    except (json.JSONDecodeError, ValueError) as e:
        log.error("ERROR: FIREBASE_CREDENTIALS is invalid: %s", e)
        raise SystemExit("Firebase initialization failed.")
    
    firebase_admin.initialize_app(cred)
    return firestore.client()

def fix_timestamp_for_document(db: firestore.Client, doc_id: str) -> bool:
    """Fix timestamp field for a specific document."""
    try:
        # Get reference to the document
        doc_ref = db.collection("images").document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            log.warning("Document %s does not exist", doc_id)
            return False
        
        # Update the timestamp field with SERVER_TIMESTAMP
        doc_ref.update({
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        log.info("Successfully updated timestamp for document: %s", doc_id)
        return True
        
    except Exception as e:
        log.error("Failed to update timestamp for document %s: %s", doc_id, e)
        return False

def fix_all_timestamp_errors(db: firestore.Client, problem_docs: List[str]):
    """Fix timestamp errors for all problematic documents."""
    log.info("Starting timestamp fix for %d documents...", len(problem_docs))
    
    success_count = 0
    failed_count = 0
    
    for doc_id in problem_docs:
        if fix_timestamp_for_document(db, doc_id):
            success_count += 1
        else:
            failed_count += 1
    
    log.info("Timestamp fix completed. Success: %d, Failed: %d", success_count, failed_count)
    return success_count, failed_count

def scan_and_fix_all_documents(db: firestore.Client):
    """Scan all documents in images collection and fix timestamp issues."""
    log.info("Scanning all documents in images collection for timestamp issues...")
    
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        from datetime import datetime
        
        # Get all documents from images collection
        docs = db.collection("images").stream()
        
        fixed_count = 0
        total_count = 0
        
        for doc in docs:
            total_count += 1
            doc_data = doc.to_dict()
            
            # Check if timestamp field exists and has wrong type
            if "timestamp" in doc_data:
                timestamp_value = doc_data["timestamp"]
                
                # Check if timestamp is string, datetime, or other wrong type
                # Correct Firestore timestamps are stored as google.cloud.firestore_v1._helpers.DatetimeWithNanoseconds
                if isinstance(timestamp_value, (str, int, float, datetime)) or timestamp_value is None:
                    log.info("Fixing timestamp for document %s (current type: %s)", 
                            doc.id, type(timestamp_value).__name__)
                    
                    # Update with correct timestamp
                    doc.reference.update({
                        "timestamp": firestore.SERVER_TIMESTAMP
                    })
                    fixed_count += 1
                else:
                    # Log the type for debugging
                    log.debug("Document %s has timestamp type: %s", doc.id, type(timestamp_value).__name__)
        
        log.info("Scanned %d documents, fixed %d timestamp issues", total_count, fixed_count)
        return fixed_count, total_count
        
    except Exception as e:
        log.error("Error scanning documents: %s", e)
        return 0, 0

def main():
    """Main function to fix timestamp errors."""
    log.info("Starting timestamp error fix script...")
    
    # Initialize Firebase
    db = initialize_firebase()
    
    # List of problematic document IDs from error messages
    problem_docs = [
        "l-wenkopf-in-mandala-d3390d",
        "mandala-bl-tenmuster-543ecc"
    ]
    
    # Fix specific documents mentioned in error
    log.info("Fixing specific documents mentioned in error...")
    success_count, failed_count = fix_all_timestamp_errors(db, problem_docs)
    
    # Scan and fix all documents (optional comprehensive fix)
    log.info("Performing comprehensive scan and fix...")
    scan_fixed, scan_total = scan_and_fix_all_documents(db)
    
    log.info("Fix script completed.")
    log.info("Specific documents - Success: %d, Failed: %d", success_count, failed_count)
    log.info("Comprehensive scan - Fixed: %d out of %d total documents", scan_fixed, scan_total)

if __name__ == "__main__":
    main()