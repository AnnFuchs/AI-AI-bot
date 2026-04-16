export type Role = "patient" | "relative" | "doctor" | "admin";

export type Sex = "male" | "female";

export type StrokeType = "ischemic" | "hemorrhagic" | "unknown";

export type UserInfo = {
  phone: string;
  email?: string | null;
  date_of_birth?: string | null;
  sex?: Sex | null;
  stroke_date?: string | null;
  recurrent_stroke?: boolean | null;
  stroke_type?: StrokeType | null;
  stroke_toast_subtype?: string | null;
  stroke_hemo_subtype?: string | null;
  doctor_id?: string | null;
};

export type UserUpdate = Partial<{
  phone: string;
  email: string | null;
  date_of_birth: string | null;
  sex: Sex | null;
  stroke_date: string | null;
  recurrent_stroke: boolean | null;
  stroke_type: StrokeType | null;
  stroke_toast_subtype: string | null;
  stroke_hemo_subtype: string | null;
  role: Role | null;
}>;

export type Profile = UserInfo;
