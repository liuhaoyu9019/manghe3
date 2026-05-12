from pydantic import BaseModel, Field


# --- Auth ---

class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=20)
    password: str = Field(min_length=4, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


# --- Pet ---

class Pet(BaseModel):
    id: int
    name: str
    rarity: str
    emoji: str
    description: str
    image_url: str | None = None


class PetListResponse(BaseModel):
    pets: list[Pet]


# --- Profile ---

class ProfileResponse(BaseModel):
    username: str
    daily_pulls_remaining: int
    total_collected: int


# --- Pull ---

class PullResponse(BaseModel):
    pet: Pet
    count: int  # how many times user has this pet


# --- Collection ---

class CollectionItem(BaseModel):
    pet_id: int
    name: str
    rarity: str
    emoji: str
    count: int
    image_url: str | None = None


class CollectionResponse(BaseModel):
    collection: list[CollectionItem]


# --- Admin ---

class AdminUserItem(BaseModel):
    id: int
    username: str
    created_at: str
    collected: int


class AdminUsersResponse(BaseModel):
    users: list[AdminUserItem]


class AdminCountResponse(BaseModel):
    count: int | str


class PetUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None


class PetImageResponse(BaseModel):
    id: int
    image_url: str


# --- Error ---

class ErrorResponse(BaseModel):
    error: dict
