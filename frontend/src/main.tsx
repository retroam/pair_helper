import React from "react";
import ReactDOM from "react-dom/client";
import { ChakraProvider, extendTheme } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./styles.css";

const theme = extendTheme({
  config: {
    initialColorMode: "dark",
    useSystemColorMode: false,
  },
  fonts: {
    heading: "'Inter', system-ui, -apple-system, sans-serif",
    body: "'Inter', system-ui, -apple-system, sans-serif",
    mono: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
  },
  colors: {
    brand: {
      50: "#e6fcff",
      100: "#b3f5ff",
      200: "#80eeff",
      300: "#4de7ff",
      400: "#1ae0ff",
      500: "#00d4ff",
      600: "#00a8cc",
      700: "#007d99",
      800: "#005266",
      900: "#002833",
    },
  },
  styles: {
    global: {
      body: {
        bg: "#0a0a0f",
        color: "#e0e0e0",
      },
    },
  },
  components: {
    Button: {
      defaultProps: {
        variant: "outline",
      },
    },
    Tag: {
      defaultProps: {
        variant: "subtle",
      },
    },
  },
});

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
