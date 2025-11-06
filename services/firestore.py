from firebase_admin import firestore

db = firestore.client()

def add_doc(col, data, doc_id=None):
    if doc_id:
        db.collection(col).document(doc_id).set(data, merge=True)
        return doc_id
    ref = db.collection(col).add(data)[1]
    return ref.id

def get_doc(col, doc_id):
    snap = db.collection(col).document(doc_id).get()
    return snap.to_dict() if snap.exists else None
