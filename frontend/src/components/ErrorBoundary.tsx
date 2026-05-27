import { Component, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <p className="text-lg font-medium">Что-то пошло не так</p>
          <p className="text-sm text-muted-foreground max-w-sm">
            {this.state.error.message || "Произошла непредвиденная ошибка."}
          </p>
          <Button variant="outline" onClick={() => this.setState({ error: null })}>
            Попробовать снова
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
