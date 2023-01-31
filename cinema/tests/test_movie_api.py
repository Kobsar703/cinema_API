from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer
)

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Test title",
        "description": "Test description",
        "duration": 120,
    }

    defaults.update(params)

    return Movie.objects.create(**defaults)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_access_allowed(self):
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_list_movie(self):
        sample_movie()

        result = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_movie_by_genre(self):
        genre_one = Genre.objects.create(name="Test1")
        genre_two = Genre.objects.create(name="Test2")

        movie_one = sample_movie(title="first movie")
        movie_two = sample_movie(title="second movie")
        movie = sample_movie(title="no genre added")

        movie_one.genres.add(genre_one)
        movie_two.genres.add(genre_two)

        result = self.client.get(MOVIE_URL, {"genres": f"{movie_one.id}, {movie_two.id}"})

        serializer = MovieListSerializer(movie)
        serializer_one = MovieListSerializer(movie_one)
        serializer_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_one.data, result.data)
        self.assertIn(serializer_two.data, result.data)
        self.assertNotIn(serializer.data, result.data)

    def test_filter_movie_by_actor(self):
        actor = Actor.objects.create(first_name="Ricardo",
                                     last_name="Alonso")

        movie_one = sample_movie(title="first movie")
        movie = sample_movie(title="no actor added")

        movie_one.actors.add(actor)

        result = self.client.get(MOVIE_URL, {"actors": f"{movie_one.id}"})

        serializer = MovieListSerializer(movie)
        serializer_one = MovieListSerializer(movie_one)

        self.assertIn(serializer_one.data, result.data)
        self.assertNotIn(serializer.data, result.data)

    def test_filter_movie_by_title(self):
        movie_one = sample_movie(title="first movie")
        movie_two = sample_movie(title="second movie")

        result = self.client.get(MOVIE_URL, {"title": "first"})

        serializer_one = MovieListSerializer(movie_one)
        serializer_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_one.data, result.data)
        self.assertNotIn(serializer_two.data, result.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Test1")
        actor = Actor.objects.create(first_name="Ricardo",
                                     last_name="Alonso")

        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        result = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        genre = Genre.objects.create(name="Test1")
        actor = Actor.objects.create(first_name="Ricardo",
                                     last_name="Alonso")

        load_data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "genre": [genre.id, ],
            "actors": [actor.id, ],
        }

        result = self.client.post(MOVIE_URL, load_data)

        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "1qazcde3",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Test")
        actor = Actor.objects.create(first_name="Ricardo's",
                                     last_name="Alonso")

        load_data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "genres": [genre.id, ],
            "actors": [actor.id, ],
        }

        result = self.client.post(MOVIE_URL, load_data)

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

    def test_create_check_content(self):
        genre_one = Genre.objects.create(name="Test1")
        genre_two = Genre.objects.create(name="Test2")
        actor_one = Actor.objects.create(first_name="Ricardo",
                                         last_name="Alonso")
        actor_two = Actor.objects.create(first_name="Ricardo",
                                         last_name="Alonso's")
        load_data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "genres": [genre_one.id, genre_two.id],
            "actors": [actor_one.id, actor_two.id],
        }

        result = self.client.post(MOVIE_URL, load_data)
        movie = Movie.objects.get(id=result.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        result = self.client.delete(url)
        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        result = self.client.put(url)
        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_upload_image_page(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])

        result = self.client.post(url)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
