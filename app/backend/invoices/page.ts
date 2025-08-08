// app/backend/invoices/page.ts

import { z } from 'zod';
import { prisma } from '../../api/lib/prisma';

// Schema for validation
const schema = z.object({
  clientId: z.string(),
  invoiceType: z.string(),
  invoiceDate: z.string(),
  dueDate: z.string(),
  accountName: z.string(),
  sortCode: z.string(),
  accountNumber: z.string(),
  iban: z.string().optional(),
  services: z.array(z.object({
    description: z.string(),
    price: z.number(),
  })),
  total: z.number(),
});

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const data = schema.parse(body);

    const invoice = await prisma.invoice.create({
      data: {
        clientId: data.clientId,
        invoiceType: data.invoiceType,
        invoiceDate: new Date(data.invoiceDate),
        dueDate: new Date(data.dueDate),
        total: data.total,
        accountName: data.accountName,
        sortCode: data.sortCode,
        accountNumber: data.accountNumber,
        iban: data.iban || null,
        services: {
          create: data.services.map(service => ({
            description: service.description,
            price: service.price,
          })),
        },
      },
      include: { services: true }, // optional
    });

    return new Response(JSON.stringify(invoice), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('API error:', err);
    return new Response(JSON.stringify({ error: 'Invalid data or server error.' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
