import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';

const app = express();
const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: '*', // Пізніше можна вказати домен фронтенду
    methods: ['GET', 'POST']
  }
});

app.use(cors());
app.use(express.json());

let usersOnline = new Map();

io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  socket.on('login', (userId) => {
    usersOnline.set(userId, socket.id);
    io.emit('userStatus', { userId, status: 'online' });
  });

  socket.on('sendMessage', (msg) => {
    io.to(msg.roomId).emit('newMessage', msg);
  });

  socket.on('joinRoom', (roomId) => {
    socket.join(roomId);
  });

  socket.on('disconnect', () => {
    // TODO: обробка офлайн статусів
  });
});

const PORT = process.env.PORT || 3001;

server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
