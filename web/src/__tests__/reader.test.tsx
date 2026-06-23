import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";

describe("reader app", () => {
  test("renders a focused report reader with quick citation review", async () => {
    const user = userEvent.setup();

    render(<App />);

    expect(
      screen.getByRole("heading", { name: "A股招股书证据阅读台" })
    ).toBeInTheDocument();
    expect(screen.getByText("文档")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /业务与技术/ })).toBeInTheDocument();
    expect(screen.getByText("核心判断")).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: /查看引用 CITE-001/ }).length
    ).toBeGreaterThan(0);
    expect(
      screen.queryByRole("navigation", { name: "报告目录" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /查看引用 CITE-002/ }));

    expect(screen.getByText("引用 CITE-002")).toBeInTheDocument();
    expect(screen.getByText("招股说明书 第 126 页")).toBeInTheDocument();
    expect(screen.getByText("source_file")).toBeInTheDocument();
  });
});
