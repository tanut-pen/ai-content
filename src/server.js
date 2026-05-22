import express from 'express';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();
const app = express();

app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ ok: true });
});

app.post('/users', async (req, res) => {
  const { email, name } = req.body;
  if (!email || !name) {
    return res.status(400).json({ error: 'email and name are required' });
  }
  const user = await prisma.user.create({ data: { email, name } });
  return res.status(201).json(user);
});

app.get('/users', async (_req, res) => {
  const users = await prisma.user.findMany({ orderBy: { id: 'asc' } });
  res.json(users);
});

app.post('/content', async (req, res) => {
  const { title, platform, status = 'draft', userId } = req.body;
  if (!title || !platform || !userId) {
    return res.status(400).json({ error: 'title, platform, userId are required' });
  }
  const content = await prisma.content.create({
    data: { title, platform, status, userId: Number(userId) }
  });
  return res.status(201).json(content);
});

app.get('/content', async (_req, res) => {
  const content = await prisma.content.findMany({ orderBy: { id: 'asc' } });
  res.json(content);
});

app.post('/metrics', async (req, res) => {
  const { contentId, impressions = 0, likes = 0, shares = 0 } = req.body;
  if (!contentId) {
    return res.status(400).json({ error: 'contentId is required' });
  }
  const metric = await prisma.metric.create({
    data: {
      contentId: Number(contentId),
      impressions: Number(impressions),
      likes: Number(likes),
      shares: Number(shares)
    }
  });
  return res.status(201).json(metric);
});

app.get('/metrics', async (_req, res) => {
  const metrics = await prisma.metric.findMany({ orderBy: { id: 'asc' } });
  res.json(metrics);
});

export function createApp() {
  return app;
}

if (process.env.NODE_ENV !== 'test' && process.env.DISABLE_AUTOSTART !== '1') {
  const port = Number(process.env.PORT || 3000);
  app.listen(port, () => {
    // eslint-disable-next-line no-console
    console.log(`Server listening on ${port}`);
  });
}
