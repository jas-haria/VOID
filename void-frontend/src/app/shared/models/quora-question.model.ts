export interface QuoraQuestion {
    id: number;
    question_text: string;
    question_url: string;
    division: number;
    asked_on: Date;
    evaluated: boolean;
}