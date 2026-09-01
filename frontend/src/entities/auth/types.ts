export type AuthCredentials = {
  login: string;
  password: string;
};

export type RegisterRequest = {
  phone: string;
  password: string;
};

export type AuthToken = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type RefreshTokenRequest = {
  refresh_token: string;
};
