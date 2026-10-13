"""Deterministic, approval-bound reply choices; actual provider sends remain gated."""
def choices(kind, quantity=1):
    if kind in ('reorder_check', 'reminder'):
        return [{'id':'reorder','title':'Reorder'}, {'id':'remind_later','title':'Remind me later'}, {'id':'get_help','title':'Get help'}]
    if kind == 'confirm_item':
        return [{'id':'same_item','title':f'Same item × {quantity}'}, {'id':'change_quantity','title':'Change quantity'}, {'id':'not_now','title':'Not now'}]
    return []

def followup_text(step, title, quantity=1):
    if step == 'confirm_item': return f'Would you like the same variant and quantity? {title} · quantity {quantity}. You can also type a question.'
    if step == 'choose_reminder': return 'What exact date and time would you prefer for a WhatsApp reminder? Please include your timezone. We will confirm it before saving.'
    return None
