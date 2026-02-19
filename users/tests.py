from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class RegisterTest(APITestCase):
    """Тесты регистрации пользователя."""

    def test_register_success(self):
        """Регистрация с корректными данными → 201 + токены."""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'testpass123',
        }
        response = self.client.post('/api/auth/register/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['username'], 'newuser')
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_short_password(self):
        """Пароль < 6 символов → 400."""
        data = {'username': 'user2', 'password': '123'}
        response = self.client.post('/api/auth/register/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """Повторный username → 400."""
        User.objects.create_user('taken', password='testpass123')
        data = {'username': 'taken', 'password': 'testpass123'}
        response = self.client.post('/api/auth/register/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_no_auth_required(self):
        """Регистрация доступна без токена (AllowAny)."""
        data = {'username': 'anon', 'password': 'testpass123'}
        response = self.client.post('/api/auth/register/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class JWTAuthTest(APITestCase):
    """Тесты JWT-аутентификации."""

    def setUp(self):
        self.user = User.objects.create_user(
            'athlete', password='testpass123',
        )

    def test_obtain_token(self):
        """Логин → получение access + refresh."""
        data = {'username': 'athlete', 'password': 'testpass123'}
        response = self.client.post('/api/auth/token/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_obtain_token_wrong_password(self):
        """Неверный пароль → 401."""
        data = {'username': 'athlete', 'password': 'wrong'}
        response = self.client.post('/api/auth/token/', data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        """Обновление access через refresh."""
        # Получаем токены
        data = {'username': 'athlete', 'password': 'testpass123'}
        tokens = self.client.post('/api/auth/token/', data).data

        # Обновляем
        response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': tokens['refresh']},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_api_without_token(self):
        """Запрос без токена → 401."""
        response = self.client.get('/api/workouts/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
