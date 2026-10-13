// Display fixtures only. Their state and simulated commands come from the server.
export const people = {
  ananya: { name:'Ananya Sharma',id:'C001',channel:'WhatsApp',status:'Reminder confirmed',date:'16 Oct, 10:00 IST',
    words:'I still have enough. Remind me Friday.', basis:'Two delivered-purchase intervals; customer-confirmed reminder.',
    timeline:['Agent: Would you like to reorder the same laundry liquid?','Ananya: I still have enough. Remind me Friday.','Agent: Reminder confirmed for 16 October at 10:00 IST.'] },
  rahul: { name:'Rahul Mehta',id:'C002',channel:'Voice → WhatsApp',status:'Checkout awaiting approval',date:'12 Oct, 11:42 IST',
    words:'Yes, the same bottle. Send me checkout on WhatsApp.',basis:'Product-level repeat estimate; exact product and one unit confirmed.',
    timeline:['Voice assistant: Would you like the same 1 L laundry liquid?','Rahul: Yes, one bottle. Send checkout on WhatsApp.','Action held: Checkout handoff awaits merchant approval.'] },
  meera: { name:'Meera Shah',id:'C003',channel:'Brand order',status:'Order confirmed',date:'12 Oct, 12:15 IST',
    words:'Purchase detected outside the agent checkout link.',basis:'Synthetic brand order and matched payment evidence.',
    timeline:['Brand order received outside agent link.','Payment and order reconciled in the demo fixture.','Competing reorder outreach cancelled.'] },
  support: { name:'Priya Nair',id:'C006',channel:'WhatsApp',status:'Delivery issue',date:'12 Oct, 09:32 IST',
    words:'My last order still has not arrived.',basis:'Unresolved delivery issue. Outside the outbound audience.',
    timeline:['Priya: My last order still has not arrived.','Sales progression stopped.','Support case needs an owner.'] },
  opted: { name:'Customer C005',id:'C005',channel:'WhatsApp',status:'Suppressed',date:'12 Oct, 08:00 IST',
    words:'Please stop contacting me.',basis:'Explicit marketing opt-out.',
    timeline:['Opt-out received.','Marketing suppressed across relevant channels.','Queued outreach cancelled.'] },
} as const;
export type PersonKey = keyof typeof people;
export const audience = ['ananya','rahul','meera'] as const;
export function fixtureBasis(key:PersonKey,playback:boolean){
  if(playback||key==='support'||key==='opted')return people[key].basis;
  if(key==='ananya')return 'Two delivered-purchase intervals suggest the repeat window. No new customer reply.';
  if(key==='rahul')return 'Product-level repeat estimate; limited customer history. SKU and quantity need confirmation.';
  return 'Qualifying delivered same-variant history; no new purchase confirmed in this scenario.';
}
